# Changelog

All notable changes to MiroFish will be documented in this file.

## [0.2.0.1] - 2026-03-28

### Added
- OAuth2 authentication with Google and GitHub providers via Authlib
- SQLite user model with Flask-Login integration and atomic upsert
- User-scoped file storage: simulations, reports, and uploads isolated per user
- Route protection middleware with default-deny when auth is enabled
- Frontend auth UI with Vue router guards and login page
- Enhanced `/health` endpoint with uptime, version, timestamp, and Zep connectivity check
- 30-second cache on Zep health checks to prevent DoS amplification
- Path traversal protection on all user-scoped file operations
- Dev-mode fallback: deterministic dev user for local development without OAuth
- 44 tests covering user model, route protection, health endpoint, and path helpers

### Fixed
- `_safe_resolve` now resolves base path with `realpath` to handle symlinks (e.g. macOS `/tmp`)
- `not_configured` Zep status no longer falsely reports `degraded`
- Raw exceptions no longer leak on public `/health` endpoint
- Cross-user directory scans removed from SimulationRunner and ReportManager
- Missing `_register_sim_user` calls on prepare/start simulation paths
- Missing `_register_report_user` call on generate report path
- Incorrect loop variable in `get_simulation_history` user registration
