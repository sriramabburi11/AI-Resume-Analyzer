import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import UploadSection from './components/UploadSection';
import Dashboard from './components/Dashboard';
import HistorySection from './components/HistorySection';
import ProfileModal from './components/ProfileModal';
import AuthPage from './components/auth/AuthPage';
import { analyzeResume } from './services/api';
import { Loader2, ShieldCheck, Sparkles } from 'lucide-react';

function MainApp() {
  const { user, session, loading } = useAuth();

  const [activeView, setActiveView] = useState('analyze'); // 'analyze' | 'history'
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const handleAnalyze = async (file, jobDescription) => {
    setIsLoading(true);
    setError(null);
    try {
      const token = session?.access_token;
      const data = await analyzeResume(file, jobDescription, token);
      setAnalysisResult(data);
    } catch (err) {
      console.error('Failed to analyze resume:', err);
      setError(err.message || 'An unexpected error occurred during resume analysis.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setAnalysisResult(null);
    setError(null);
    setActiveView('analyze');
  };

  const handleSelectHistoryItem = (fullAnalysis) => {
    setAnalysisResult(fullAnalysis);
    setActiveView('analyze');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center mb-4 shadow-lg shadow-blue-500/25">
          <Sparkles className="w-6 h-6 animate-pulse" />
        </div>
        <Loader2 className="w-6 h-6 text-blue-600 animate-spin mb-2" />
        <p className="text-sm font-semibold text-slate-700">Verifying secure session...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <Navbar
        activeView={activeView}
        setActiveView={setActiveView}
        onReset={handleReset}
        onOpenProfile={() => setIsProfileOpen(true)}
      />

      <main className="flex-1 pb-16">
        {!user ? (
          /* Unauthenticated user: Show Authentication View (Login/Register/Reset) */
          <AuthPage />
        ) : (
          /* Authenticated user: Protected Views */
          <>
            {activeView === 'analyze' && (
              <>
                {!analysisResult ? (
                  <UploadSection
                    onAnalyze={handleAnalyze}
                    isLoading={isLoading}
                    error={error}
                    setError={setError}
                  />
                ) : (
                  <Dashboard
                    data={analysisResult}
                    onReset={handleReset}
                    onBackToHistory={() => setActiveView('history')}
                  />
                )}
              </>
            )}

            {activeView === 'history' && (
              <HistorySection
                onSelectAnalysis={handleSelectHistoryItem}
                onUploadNew={handleReset}
              />
            )}

            {/* Profile / Account Settings Modal */}
            <ProfileModal
              isOpen={isProfileOpen}
              onClose={() => setIsProfileOpen(false)}
            />
          </>
        )}
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>© {new Date().getFullYear()} AI Resume Analyzer & ATS Optimizer. Built for High-Impact Technical Applications.</p>
          <div className="flex items-center gap-1.5 text-slate-400">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>PostgreSQL Database & Secure Auth</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
