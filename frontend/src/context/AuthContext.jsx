import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  registerUser,
  loginUser,
  logoutUser,
  fetchCurrentUser,
  forgotPassword,
  resetPassword,
  updateProfile
} from '../services/api';

const AuthContext = createContext(null);
const TOKEN_KEY = 'resume_pulse_auth_token';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(true);
  const [authView, setAuthView] = useState('login'); // 'login' | 'register' | 'forgot_password' | 'reset_password'
  const [resetToken, setResetToken] = useState(null);

  // Check URL parameters for password reset tokens on initial load
  useEffect(() => {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const urlToken = urlParams.get('token') || urlParams.get('reset_token');
      if (urlToken) {
        setResetToken(urlToken);
        setAuthView('reset_password');
      }
    } catch (e) {
      console.warn('URL token parse error:', e);
    }
  }, []);

  // Verify and load user session on mount or token change
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      if (!storedToken) {
        setUser(null);
        setToken(null);
        setLoading(false);
        return;
      }

      try {
        const userData = await fetchCurrentUser(storedToken);
        setUser(userData);
        setToken(storedToken);
      } catch (err) {
        console.warn('Session verification failed, clearing stale token:', err.message);
        localStorage.removeItem(TOKEN_KEY);
        setUser(null);
        setToken(null);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const signUp = async ({ email, password, fullName }) => {
    const authData = await registerUser({
      fullName,
      email,
      password,
    });

    const jwtToken = authData.access_token;
    localStorage.setItem(TOKEN_KEY, jwtToken);
    setToken(jwtToken);
    setUser(authData.user);
    return { user: authData.user, token: jwtToken };
  };

  const signIn = async ({ email, password }) => {
    const authData = await loginUser({ email, password });
    const jwtToken = authData.access_token;
    localStorage.setItem(TOKEN_KEY, jwtToken);
    setToken(jwtToken);
    setUser(authData.user);
    return { user: authData.user, token: jwtToken };
  };

  const signOut = async () => {
    await logoutUser();
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setToken(null);
    setAuthView('login');
  };

  const requestPasswordReset = async (email) => {
    return await forgotPassword(email);
  };

  const handleUpdatePassword = async (newPassword) => {
    if (!resetToken) {
      throw new Error('Missing password reset token. Please use the link provided in your reset instructions.');
    }
    const res = await resetPassword({ token: resetToken, newPassword });
    setResetToken(null);
    setAuthView('login');
    return res;
  };

  const updateProfileName = async (fullName) => {
    if (!token) return;
    const updated = await updateProfile(fullName, token);
    setUser(prev => ({ ...prev, full_name: updated.full_name }));
    return updated;
  };

  const value = {
    user,
    token,
    session: token ? { access_token: token } : null,
    profile: user,
    loading,
    authView,
    setAuthView,
    resetToken,
    setResetToken,
    signUp,
    signIn,
    signOut,
    requestPasswordReset,
    updatePassword: handleUpdatePassword,
    updateProfileName,
    refreshProfile: async () => {
      if (token) {
        const u = await fetchCurrentUser(token);
        setUser(u);
      }
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
