import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../services/supabaseClient';
import { registerUser, loginUser, verifyEmail, resendVerification } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authView, setAuthView] = useState('login'); // 'login' | 'register' | 'verify_otp' | 'forgot_password' | 'reset_password'
  const [pendingEmail, setPendingEmail] = useState('');
  const [resetToken, setResetToken] = useState(null);

  // Helper to format user object
  const formatUser = (supabaseUser) => {
    if (!supabaseUser) return null;
    const meta = supabaseUser.user_metadata || {};
    return {
      id: supabaseUser.id,
      email: supabaseUser.email,
      full_name: meta.full_name || meta.name || (supabaseUser.email ? supabaseUser.email.split('@')[0] : 'User'),
      user_metadata: meta,
      created_at: supabaseUser.created_at,
    };
  };

  useEffect(() => {
    // 1. Initial session load
    const initSession = async () => {
      try {
        const { data: { session: initialSession }, error } = await supabase.auth.getSession();
        if (error) {
          console.warn('Supabase getSession error:', error.message);
        }
        if (initialSession) {
          setSession(initialSession);
          setUser(formatUser(initialSession.user));
        }
      } catch (err) {
        console.error('Error initializing Supabase session:', err);
      } finally {
        setLoading(false);
      }
    };

    initSession();

    // 2. Listen to Supabase auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, newSession) => {
      if (newSession) {
        setSession(newSession);
        setUser(formatUser(newSession.user));
      } else {
        setSession(null);
        setUser(null);
      }

      if (event === 'PASSWORD_RECOVERY') {
        setAuthView('reset_password');
      }

      setLoading(false);
    });

    // Check URL parameters for password reset flow
    try {
      const hash = window.location.hash;
      const search = window.location.search;
      if (hash.includes('type=recovery') || search.includes('type=recovery')) {
        setAuthView('reset_password');
      }
    } catch (e) {
      // safe fallback
    }

    return () => {
      subscription?.unsubscribe();
    };
  }, []);

  const signUp = async ({ email, password, fullName }) => {
    const cleanEmail = email.trim().toLowerCase();
    const cleanName = fullName.trim();

    const res = await registerUser({
      fullName: cleanName,
      email: cleanEmail,
      password,
    });

    setPendingEmail(cleanEmail);
    setAuthView('verify_otp');
    return res;
  };

  const signIn = async ({ email, password }) => {
    const cleanEmail = email.trim().toLowerCase();

    try {
      const res = await loginUser({ email: cleanEmail, password });
      if (res?.access_token) {
        const userObj = {
          id: res.user.id,
          email: res.user.email,
          full_name: res.user.full_name,
          email_verified: true,
          user_metadata: { full_name: res.user.full_name, email_verified: true },
        };
        setSession({ access_token: res.access_token, user: userObj });
        setUser(userObj);

        // Sync with Supabase client SDK in background
        try {
          await supabase.auth.signInWithPassword({ email: cleanEmail, password });
        } catch (syncErr) {
          // Local bearer token is already active
        }
      }
      return res;
    } catch (err) {
      if (err.requiresVerification || err.status === 403) {
        setPendingEmail(cleanEmail);
        setAuthView('verify_otp');
      }
      throw err;
    }
  };

  const verifyOtp = async ({ email, otp }) => {
    const targetEmail = (email || pendingEmail).trim().toLowerCase();
    const res = await verifyEmail({ email: targetEmail, otp: otp.trim() });

    if (res?.access_token) {
      const userObj = {
        id: res.user.id,
        email: res.user.email,
        full_name: res.user.full_name,
        email_verified: true,
        user_metadata: { full_name: res.user.full_name, email_verified: true },
      };
      setSession({ access_token: res.access_token, user: userObj });
      setUser(userObj);
      setPendingEmail('');
      setAuthView('login');
    }

    return res;
  };

  const resendOtp = async (emailOverride) => {
    const targetEmail = (emailOverride || pendingEmail).trim().toLowerCase();
    if (!targetEmail) {
      throw new Error('No email address specified for verification.');
    }
    return await resendVerification({ email: targetEmail });
  };

  const signOut = async () => {
    try {
      await supabase.auth.signOut();
    } catch (err) {
      console.warn('Supabase signOut notice:', err);
    }
    setSession(null);
    setUser(null);
    setPendingEmail('');
    setAuthView('login');
  };

  const requestPasswordReset = async (email) => {
    const { data, error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${window.location.origin}/`,
    });

    if (error) {
      throw error;
    }

    return { message: 'Password reset link sent to your email.' };
  };

  const handleUpdatePassword = async (newPassword) => {
    const { data, error } = await supabase.auth.updateUser({
      password: newPassword,
    });

    if (error) {
      throw error;
    }

    setAuthView('login');
    return { message: 'Password updated successfully!' };
  };

  const updateProfileName = async (fullName) => {
    const { data, error } = await supabase.auth.updateUser({
      data: {
        full_name: fullName.trim(),
      },
    });

    if (error) {
      throw error;
    }

    if (data?.user) {
      setUser(formatUser(data.user));
    }
    return data;
  };

  const value = {
    user,
    token: session?.access_token || null,
    session,
    profile: user,
    loading,
    authView,
    setAuthView,
    pendingEmail,
    setPendingEmail,
    resetToken,
    setResetToken,
    signUp,
    signIn,
    verifyOtp,
    resendOtp,
    signOut,
    requestPasswordReset,
    updatePassword: handleUpdatePassword,
    updateProfileName,
    refreshProfile: async () => {
      const { data: { user: u } } = await supabase.auth.getUser();
      if (u) setUser(formatUser(u));
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
