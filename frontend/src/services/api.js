const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

function getAuthHeaders(token) {
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) throw new Error('Health check failed');
    return await response.json();
  } catch (err) {
    console.error('API health check error:', err);
    throw err;
  }
}

// ==============================================================================
// Authentication API (Self-managed Backend)
// ==============================================================================

export async function registerUser({ fullName, email, password }) {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Registration failed. Please try again.');
  }

  return await response.json();
}

export async function loginUser({ email, password }) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Invalid email or password.');
  }

  return await response.json();
}

export async function logoutUser() {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST' });
  } catch (err) {
    console.error('Logout error:', err);
  }
}

export async function fetchCurrentUser(token) {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(token),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to verify session.');
  }

  return await response.json();
}

export async function forgotPassword(email) {
  const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to process password reset request.');
  }

  return await response.json();
}

export async function resetPassword({ token, newPassword }) {
  const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token,
      new_password: newPassword,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to reset password. Link may be invalid or expired.');
  }

  return await response.json();
}

export async function updateProfile(fullName, token) {
  const response = await fetch(`${API_BASE_URL}/auth/profile`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(token),
    },
    body: JSON.stringify({ full_name: fullName }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to update profile.');
  }

  return await response.json();
}

// ==============================================================================
// Resume Analysis & History API
// ==============================================================================

export async function analyzeResume(file, jobDescription = '', token = null) {
  const formData = new FormData();
  formData.append('resume', file);
  
  if (jobDescription && jobDescription.trim()) {
    formData.append('job_description', jobDescription.trim());
  }

  const headers = getAuthHeaders(token);

  const response = await fetch(`${API_BASE_URL}/analyze-resume`, {
    method: 'POST',
    headers: headers,
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.detail || `Server error (${response.status})`;
    throw new Error(message);
  }

  return await response.json();
}

export async function fetchHistory(token) {
  const response = await fetch(`${API_BASE_URL}/history`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(token),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch history (${response.status})`);
  }

  return await response.json();
}

export async function fetchHistoryDetail(analysisId, token) {
  const response = await fetch(`${API_BASE_URL}/history/${analysisId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(token),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch analysis details (${response.status})`);
  }

  return await response.json();
}

export async function deleteHistoryItem(analysisId, token) {
  const response = await fetch(`${API_BASE_URL}/history/${analysisId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(token),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete analysis (${response.status})`);
  }

  return await response.json();
}
