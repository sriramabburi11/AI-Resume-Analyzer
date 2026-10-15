import React, { useState } from 'react';
import {
  FileText,
  Sparkles,
  Lock,
  Mail,
  User,
  ArrowRight,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle2,
  Loader2,
  KeyRound,
  ShieldCheck,
  Key
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function AuthPage() {
  const {
    authView,
    setAuthView,
    signIn,
    signUp,
    requestPasswordReset,
    updatePassword,
    resetToken,
    setResetToken,
  } = useAuth();

  // Form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [manualToken, setManualToken] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Status states
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const clearMessages = () => {
    setErrorMessage('');
    setSuccessMessage('');
  };

  const handleSwitchView = (newView) => {
    clearMessages();
    setPassword('');
    setConfirmPassword('');
    setAuthView(newView);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearMessages();

    // Validation
    if (authView === 'register') {
      if (!fullName.trim()) {
        setErrorMessage('Please enter your full name.');
        return;
      }
      if (password.length < 6) {
        setErrorMessage('Password must be at least 6 characters long.');
        return;
      }
      if (password !== confirmPassword) {
        setErrorMessage('Passwords do not match. Please verify your password confirmation.');
        return;
      }
    }

    if (authView === 'reset_password') {
      const activeToken = resetToken || manualToken.trim();
      if (!activeToken) {
        setErrorMessage('Please enter your password reset token.');
        return;
      }
      if (password.length < 6) {
        setErrorMessage('Password must be at least 6 characters long.');
        return;
      }
      if (password !== confirmPassword) {
        setErrorMessage('Passwords do not match.');
        return;
      }
    }

    setIsLoading(true);

    try {
      if (authView === 'login') {
        await signIn({ email: email.trim(), password });
      } else if (authView === 'register') {
        await signUp({
          email: email.trim(),
          password,
          fullName: fullName.trim(),
        });
      } else if (authView === 'forgot_password') {
        if (!email.trim()) {
          setErrorMessage('Please enter the email associated with your account.');
          setIsLoading(false);
          return;
        }

        const res = await requestPasswordReset(email.trim());
        setSuccessMessage(
          res.message || 'Password reset instructions have been generated. Please check your email inbox.'
        );
      } else if (authView === 'reset_password') {
        if (!resetToken && manualToken) {
          setResetToken(manualToken.trim());
        }
        await updatePassword(password);
        setSuccessMessage('Password updated successfully! You can now access your dashboard.');
        setAuthView('login');
      }
    } catch (err) {
      console.error('Authentication error:', err);
      let msg = err.message || 'An error occurred during authentication.';
      if (msg.toLowerCase().includes('invalid email or password')) {
        msg = 'Invalid email or password. Please verify your credentials and try again.';
      } else if (msg.toLowerCase().includes('already exists')) {
        msg = 'An account with this email address already exists. Please sign in instead.';
      }
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex flex-col justify-center py-12 sm:px-6 lg:px-8 fade-in">
      {/* Brand Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-2">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-500/25 mb-1">
          <FileText className="w-6 h-6" />
        </div>
        <div className="flex items-center justify-center gap-2">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            ResumePulse
          </h2>
          <span className="bg-blue-50 text-blue-700 text-xs font-bold px-2 py-0.5 rounded-full border border-blue-200 flex items-center gap-1">
            <Sparkles className="w-3 h-3" /> ATS AI
          </span>
        </div>
        <p className="text-sm text-slate-500 max-w-sm mx-auto">
          {authView === 'login' && 'Sign in to analyze resumes and track your ATS score history.'}
          {authView === 'register' && 'Create your account to unlock AI-powered resume optimization.'}
          {authView === 'forgot_password' && 'Enter your email to receive a secure password reset link.'}
          {authView === 'reset_password' && 'Enter your new password below to regain account access.'}
        </p>
      </div>

      {/* Auth Card Container */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 rounded-2xl border border-slate-200 shadow-xl shadow-slate-200/50 space-y-6">
          {/* Form Header Tabs (Login vs Register) */}
          {(authView === 'login' || authView === 'register') && (
            <div className="flex rounded-xl bg-slate-100 p-1">
              <button
                type="button"
                onClick={() => handleSwitchView('login')}
                className={`flex-1 py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer ${
                  authView === 'login'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => handleSwitchView('register')}
                className={`flex-1 py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer ${
                  authView === 'register'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Create Account
              </button>
            </div>
          )}

          {/* Error Banner */}
          {errorMessage && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3.5 flex items-start gap-2.5 text-xs sm:text-sm text-red-800 fade-in">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 font-medium leading-relaxed">{errorMessage}</div>
            </div>
          )}

          {/* Success Banner */}
          {successMessage && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 flex items-start gap-2.5 text-xs sm:text-sm text-emerald-800 fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 font-medium leading-relaxed">{successMessage}</div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name (Sign Up only) */}
            {authView === 'register' && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Full Name <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Alex Mercer"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-slate-800 placeholder-slate-400 transition"
                  />
                </div>
              </div>
            )}

            {/* Email (Login, Register, Forgot Password) */}
            {authView !== 'reset_password' && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Email Address <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="alex.mercer@example.com"
                    autoComplete="email"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-slate-800 placeholder-slate-400 transition"
                  />
                </div>
              </div>
            )}

            {/* Reset Token Input if not provided via URL */}
            {authView === 'reset_password' && !resetToken && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Reset Token <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Key className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={manualToken}
                    onChange={(e) => setManualToken(e.target.value)}
                    placeholder="Paste reset token here..."
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-slate-800 placeholder-slate-400 transition"
                  />
                </div>
              </div>
            )}

            {/* Password (Login, Register, Reset Password) */}
            {authView !== 'forgot_password' && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-slate-700">
                    {authView === 'reset_password' ? 'New Password' : 'Password'}{' '}
                    <span className="text-red-500">*</span>
                  </label>
                  {authView === 'login' && (
                    <button
                      type="button"
                      onClick={() => handleSwitchView('forgot_password')}
                      className="text-xs text-blue-600 hover:text-blue-700 font-medium cursor-pointer"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete={authView === 'login' ? 'current-password' : 'new-password'}
                    className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-slate-200 text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-slate-800 placeholder-slate-400 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 cursor-pointer"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {authView === 'register' && (
                  <p className="text-[11px] text-slate-400 mt-1">Must be at least 6 characters long.</p>
                )}
              </div>
            )}

            {/* Confirm Password (Register, Reset Password) */}
            {(authView === 'register' || authView === 'reset_password') && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Confirm Password <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <KeyRound className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete="new-password"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none text-slate-800 placeholder-slate-400 transition"
                  />
                </div>
              </div>
            )}

            {/* Submit Action Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 px-4 rounded-xl font-semibold text-white text-sm bg-blue-600 hover:bg-blue-700 active:scale-[0.99] shadow-md shadow-blue-500/20 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Please wait...</span>
                  </>
                ) : (
                  <>
                    <span>
                      {authView === 'login' && 'Sign In to Dashboard'}
                      {authView === 'register' && 'Create Free Account'}
                      {authView === 'forgot_password' && 'Send Reset Instructions'}
                      {authView === 'reset_password' && 'Save New Password'}
                    </span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Footer Navigation */}
          {authView === 'forgot_password' && (
            <div className="text-center pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => handleSwitchView('login')}
                className="text-xs text-blue-600 hover:text-blue-700 font-semibold cursor-pointer"
              >
                ← Back to Sign In
              </button>
            </div>
          )}

          {/* Privacy Note */}
          <div className="pt-2 border-t border-slate-100 text-center">
            <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>In-memory resume processing • Secure Supabase Authentication</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
