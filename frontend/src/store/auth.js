import { reactive } from 'vue'
import { checkAuth as fetchAuthStatus } from '../api/auth'

/**
 * Reactive auth state shared across the app.
 *
 *   authEnabled  - server requires login (AUTH_ENABLED=true)
 *   authenticated - user has a valid session
 *   user         - { id, email, display_name, avatar_url, provider }
 *   checked      - initial auth check has completed
 */
export const authState = reactive({
  authEnabled: false,
  authenticated: false,
  user: null,
  checked: false,
})

/**
 * Call the backend to check auth status.
 * Safe to call multiple times -- subsequent calls are debounced until the
 * first one resolves.
 */
let checkPromise = null
export async function checkAuth() {
  if (checkPromise) return checkPromise

  checkPromise = (async () => {
    try {
      const data = await fetchAuthStatus()
      authState.authEnabled = data.auth_enabled
      authState.authenticated = data.authenticated
      authState.user = data.user
    } catch {
      // If the request fails, assume auth is required and user is not
      // authenticated. Setting authEnabled=true prevents the guard from
      // silently letting unauthenticated users through on network errors.
      authState.authEnabled = true
      authState.authenticated = false
      authState.user = null
    } finally {
      authState.checked = true
      checkPromise = null
    }
  })()

  return checkPromise
}

export function clearAuth() {
  authState.authenticated = false
  authState.user = null
  authState.checked = false
}
