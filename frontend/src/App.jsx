import React, { useState } from 'react';
import Navbar from './components/Navbar';
import UploadSection from './components/UploadSection';
import Dashboard from './components/Dashboard';
import { analyzeResume } from './services/api';

export default function App() {
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async (file, jobDescription) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await analyzeResume(file, jobDescription);
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
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <Navbar onReset={handleReset} />

      <main className="flex-1 pb-16">
        {!analysisResult ? (
          <UploadSection
            onAnalyze={handleAnalyze}
            isLoading={isLoading}
            error={error}
            setError={setError}
          />
        ) : (
          <Dashboard data={analysisResult} onReset={handleReset} />
        )}
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4">
          <p>© {new Date().getFullYear()} AI Resume Analyzer & ATS Optimizer. Built for High-Impact Technical Applications.</p>
        </div>
      </footer>
    </div>
  );
}
