import React from 'react';
import {
  FileText,
  Sparkles,
  ShieldCheck,
  History,
  User,
  LogOut,
  UploadCloud
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Navbar({ activeView, setActiveView, onReset, onOpenProfile }) {
  const { user, profile, signOut, setAuthView } = useAuth();

  const displayName = profile?.full_name || user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <header className="sticky top-0 z-50 bg-white/85 backdrop-blur-md border-b border-slate-200/80 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div
          className="flex items-center gap-3 cursor-pointer select-none"
          onClick={onReset}
        >
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-slate-900 tracking-tight">ResumePulse</span>
              <span className="bg-blue-50 text-blue-700 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-blue-200 flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> ATS AI
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">AI Resume Analyzer & ATS Optimizer</p>
          </div>
        </div>

        {/* Center Navigation Tabs (Only when authenticated) */}
        {user && (
          <div className="hidden md:flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => setActiveView('analyze')}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
                activeView === 'analyze'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Resume Analyzer</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveView('history')}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
                activeView === 'history'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>Saved History</span>
            </button>
          </div>
        )}

        {/* Right Action Controls */}
        <div className="flex items-center gap-3">
          {/* Privacy Guard Notice */}
          <div className="hidden lg:flex items-center gap-2 text-xs font-medium text-slate-600 bg-slate-100/80 px-3 py-1.5 rounded-lg border border-slate-200">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Privacy Guard: Files processed in-memory</span>
          </div>

          {user ? (
            <div className="flex items-center gap-2">
              {/* Profile Pill */}
              <button
                type="button"
                onClick={onOpenProfile}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-700 transition cursor-pointer"
                title="View account profile"
              >
                <div className="w-6 h-6 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs">
                  {initial}
                </div>
                <span className="hidden sm:inline max-w-[120px] truncate">{displayName}</span>
              </button>

              {/* Mobile History Toggle */}
              <button
                type="button"
                onClick={() => setActiveView(activeView === 'history' ? 'analyze' : 'history')}
                className="md:hidden p-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 cursor-pointer"
                title="Toggle History"
              >
                <History className="w-4 h-4" />
              </button>

              {/* Logout Button */}
              <button
                type="button"
                onClick={signOut}
                className="p-2 rounded-xl border border-slate-200 hover:bg-red-50 hover:border-red-200 text-slate-500 hover:text-red-600 transition cursor-pointer"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setAuthView('login')}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 cursor-pointer"
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => setAuthView('register')}
                className="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs transition cursor-pointer"
              >
                Get Started
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
