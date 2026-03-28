import service from './index'

/**
 * Check current authentication status.
 * Returns { auth_enabled, authenticated, user }
 */
export function checkAuth() {
  return service.get('/api/auth/status')
}

/**
 * Log out the current user.
 */
export function logout() {
  return service.post('/api/auth/logout')
}

/**
 * Get the OAuth login URL for a provider.
 * Returns a full URL string -- the caller should navigate to it.
 */
export function loginUrl(provider) {
  const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001'
  return `${base}/api/auth/login/${provider}`
}
