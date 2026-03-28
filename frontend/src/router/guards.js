import { authState, checkAuth } from '../store/auth'

/**
 * Navigation guard that enforces authentication on protected routes.
 *
 * Install with:  router.beforeEach(authGuard)
 */
export async function authGuard(to, _from, next) {
  // Public routes skip auth
  if (to.meta.public) {
    return next()
  }

  // Make sure we've checked auth at least once
  if (!authState.checked) {
    await checkAuth()
  }

  // If auth is disabled server-side, let everything through
  if (!authState.authEnabled) {
    return next()
  }

  if (!authState.authenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  next()
}
