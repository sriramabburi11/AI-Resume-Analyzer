import React, { useState, useEffect, useRef } from 'react';
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
  Key,
  Clock,
  RotateCcw,
  Check,
  ArrowLeft
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function AuthPage() {
  const {
    authView,
    setAuthView,
    pendingEmail,
    setPendingEmail,
    signIn,
    signUp,
    verifyOtp,
    resendOtp,
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

  // OTP Verification states
  const [otpDigits, setOtpDigits] = useState(['', '', '', '', '', '']);
  const [cooldownSeconds, setCooldownSeconds] = useState(60);
  const [expirySeconds, setExpirySeconds] = useState(600); // 10 minutes
  const [isResending, setIsResending] = useState(false);
  const otpInputsRef = useRef([]);

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
    setOtpDigits(['', '', '', '', '', '']);
    setAuthView(newView);
  };

  // Cooldown and Expiry timers for OTP view
  useEffect(() => {
    let timer;
    if (authView === 'verify_otp') {
      // Focus first OTP input
      setTimeout(() => {
        otpInputsRef.current[0]?.focus();
      }, 100);

      timer = setInterval(() => {
        setCooldownSeconds((prev) => (prev > 0 ? prev - 1 : 0));
        setExpirySeconds((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    }

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [authView]);

  // Handle OTP digit changes
  const handleOtpChange = (index, value) => {
    // If user pasted or entered multiple numbers
    const cleanNumbers = value.replace(/\D/g, '');
    if (cleanNumbers.length > 1) {
      const newDigits = [...otpDigits];
      for (let i = 0; i < 6; i++) {
        newDigits[i] = cleanNumbers[i] || '';
      }
      setOtpDigits(newDigits);
      const nextIndex = Math.min(cleanNumbers.length, 5);
      otpInputsRef.current[nextIndex]?.focus();
      return;
    }

    const digit = cleanNumbers.slice(-1);
    const newDigits = [...otpDigits];
    newDigits[index] = digit;
    setOtpDigits(newDigits);

    // Auto-advance
    if (digit && index < 5) {
      otpInputsRef.current[index + 1]?.focus();
    }
  };

  // Handle Backspace and arrow navigation in OTP inputs
  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace') {
      if (!otpDigits[index] && index > 0) {
        otpInputsRef.current[index - 1]?.focus();
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      otpInputsRef.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < 5) {
      otpInputsRef.current[index + 1]?.focus();
    }
  };

  // Handle Paste
  const handleOtpPaste = (e) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pasteData) return;

    const newDigits = [...otpDigits];
    for (let i = 0; i < 6; i++) {
      newDigits[i] = pasteData[i] || '';
    }
    setOtpDigits(newDigits);

    const focusIndex = Math.min(pasteData.length, 5);
    otpInputsRef.current[focusIndex]?.focus();
  };

  // Handle Resend Verification Code
  const handleResendCode = async () => {
    if (cooldownSeconds > 0 || isResending) return;
    clearMessages();
    setIsResending(true);

    const targetEmail = pendingEmail || email;
    try {
      const res = await resendOtp(targetEmail);
      setSuccessMessage(res.message || 'A new 6-digit verification code has been sent to your email.');
      setCooldownSeconds(60);
      setExpirySeconds(600);
      setOtpDigits(['', '', '', '', '', '']);
      otpInputsRef.current[0]?.focus();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to resend verification code. Please try again.');
    } finally {
      setIsResending(false);
    }
  };

  // Handle Form Submit
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

    if (authView === 'verify_otp') {
      const fullCode = otpDigits.join('');
      if (fullCode.length !== 6) {
        setErrorMessage('Please enter all 6 digits of the verification code.');
        return;
      }
      if (expirySeconds <= 0) {
        setErrorMessage('Verification code has expired. Please click "Resend Code" to receive a new one.');
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
        const res = await signUp({
          email: email.trim(),
          password,
          fullName: fullName.trim(),
        });

        setSuccessMessage(
          res?.message || 'Verification code sent! Check your email inbox for your 6-digit code.'
        );
        setCooldownSeconds(60);
        setExpirySeconds(600);
      } else if (authView === 'verify_otp') {
        const fullCode = otpDigits.join('');
        await verifyOtp({
          email: pendingEmail || email.trim(),
          otp: fullCode,
        });
        setSuccessMessage('Email verified successfully! Welcome to ResumePulse.');
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
      const lower = msg.toLowerCase();

      if (err.requiresVerification || err.status === 403 || lower.includes('verification required')) {
        setErrorMessage('Please verify your email address. A 6-digit verification code has been dispatched.');
        setCooldownSeconds(60);
        setExpirySeconds(600);
        setAuthView('verify_otp');
        return;
      }

      if (lower.includes('invalid email or password') || lower.includes('invalid login credentials')) {
        msg = 'Invalid email or password. Please verify your credentials and try again.';
      } else if (lower.includes('already registered') || lower.includes('already exists')) {
        msg = 'An account with this email address already exists. Please sign in below.';
      } else if (lower.includes('cooldown') || lower.includes('wait')) {
        // Cooldown message handled directly
      }

      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTimer = (totalSeconds) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const currentEmail = pendingEmail || email || 'your email';

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
          {authView === 'verify_otp' && 'Verify your email address to activate your account.'}
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

          {/* Email Verification Header Banner */}
          {authView === 'verify_otp' && (
            <div className="text-center space-y-2 pb-1 border-b border-slate-100">
              <div className="inline-flex items-center justify-center w-11 h-11 rounded-full bg-blue-50 text-blue-600 mb-1">
                <Mail className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Check Your Inbox</h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                We've sent a 6-digit verification code to
                <br />
                <span className="font-semibold text-slate-800 break-all">{currentEmail}</span>
              </p>
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
            {authView !== 'reset_password' && authView !== 'verify_otp' && (
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

            {/* ============================================================== */}
            {/* OTP 6-Digit Segmented Input UI */}
            {/* ============================================================== */}
            {authView === 'verify_otp' && (
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-xs font-semibold text-slate-700">
                      Enter 6-Digit Code
                    </label>
                    <div className="flex items-center gap-1 text-[11px] font-medium text-slate-500">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {expirySeconds > 0 ? (
                        <span className={expirySeconds < 120 ? 'text-amber-600 font-semibold' : 'text-slate-500'}>
                          Expires in {formatTimer(expirySeconds)}
                        </span>
                      ) : (
                        <span className="text-red-600 font-semibold">Code expired</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-1.5 sm:gap-2" onPaste={handleOtpPaste}>
                    {otpDigits.map((digit, index) => (
                      <input
                        key={index}
                        ref={(el) => (otpInputsRef.current[index] = el)}
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handleOtpChange(index, e.target.value)}
                        onKeyDown={(e) => handleOtpKeyDown(index, e)}
                        className="w-10 h-12 sm:w-12 sm:h-14 text-center text-xl sm:text-2xl font-bold rounded-xl border border-slate-200 text-slate-900 bg-slate-50/50 focus:bg-white focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 outline-none transition shadow-xs"
                      />
                    ))}
                  </div>
                </div>

                {/* Resend Cooldown Counter & Action */}
                <div className="flex items-center justify-between text-xs pt-1">
                  <span className="text-slate-500">Didn't receive the email?</span>
                  <button
                    type="button"
                    onClick={handleResendCode}
                    disabled={cooldownSeconds > 0 || isResending}
                    className={`font-semibold flex items-center gap-1 transition ${
                      cooldownSeconds > 0 || isResending
                        ? 'text-slate-400 cursor-not-allowed'
                        : 'text-blue-600 hover:text-blue-700 cursor-pointer'
                    }`}
                  >
                    {isResending ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>Sending...</span>
                      </>
                    ) : cooldownSeconds > 0 ? (
                      <>
                        <RotateCcw className="w-3 h-3" />
                        <span>Resend in {cooldownSeconds}s</span>
                      </>
                    ) : (
                      <>
                        <RotateCcw className="w-3 h-3" />
                        <span>Resend Code</span>
                      </>
                    )}
                  </button>
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
            {authView !== 'forgot_password' && authView !== 'verify_otp' && (
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
                disabled={isLoading || (authView === 'verify_otp' && otpDigits.join('').length !== 6)}
                className="w-full py-2.5 px-4 rounded-xl font-semibold text-white text-sm bg-blue-600 hover:bg-blue-700 active:scale-[0.99] shadow-md shadow-blue-500/20 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
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
                      {authView === 'verify_otp' && 'Verify & Continue'}
                      {authView === 'forgot_password' && 'Send Reset Instructions'}
                      {authView === 'reset_password' && 'Save New Password'}
                    </span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Footer Navigation for OTP View */}
          {authView === 'verify_otp' && (
            <div className="text-center pt-2 border-t border-slate-100 flex items-center justify-center gap-4 text-xs">
              <button
                type="button"
                onClick={() => handleSwitchView('login')}
                className="text-slate-500 hover:text-slate-800 font-medium cursor-pointer flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Sign In</span>
              </button>
              <span className="text-slate-300">•</span>
              <button
                type="button"
                onClick={() => handleSwitchView('register')}
                className="text-blue-600 hover:text-blue-700 font-semibold cursor-pointer"
              >
                Edit Email
              </button>
            </div>
          )}

          {/* Footer Navigation for Forgot Password */}
          {authView === 'forgot_password' && (
            <div className="text-center pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => handleSwitchView('login')}
                className="text-xs text-blue-600 hover:text-blue-700 font-semibold cursor-pointer flex items-center justify-center gap-1 mx-auto"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Sign In</span>
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
