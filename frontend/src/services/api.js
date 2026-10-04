const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

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

export async function analyzeResume(file, jobDescription = '') {
  const formData = new FormData();
  formData.append('resume', file);
  
  if (jobDescription && jobDescription.trim()) {
    formData.append('job_description', jobDescription.trim());
  }

  const response = await fetch(`${API_BASE_URL}/analyze-resume`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = errorData.detail || `Server error (${response.status})`;
    throw new Error(message);
  }

  return await response.json();
}
