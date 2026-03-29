# Changelog

All notable changes to MiroFish will be documented in this file.

## [0.2.3.0] - 2026-03-29

### Fixed
- Show error banner on project load and generation failures in MainView
- Add 404 catch-all route for unknown paths with NotFound page

### Changed
- Translated entire codebase from Chinese to English (63 files, ~14K lines)
- All backend Python source: comments, docstrings, error messages, log messages, LLM prompts, variable names
- All frontend Vue/JS source: UI labels, placeholder text, status messages, component comments
- Configuration files: .env.example descriptions, Docker labels, package.json metadata
- Resolved remaining Chinese language artifacts missed in initial translation pass

## [0.2.1.1] - 2026-03-28

### Fixed
- Closed 10 IDOR gaps across entity, profile, task polling, graph, and report endpoints
- Entity list/detail and generate_profiles endpoints now verify project ownership
- Task polling user_id parameter validated against authenticated user
- Graph search, delete, and data endpoints enforce user-scoped project lookup
- Report tool endpoints (chat, interview) verify report ownership before access
- Report list returns empty array instead of 500 when user reports directory missing
- Empty SECRET_KEY no longer crashes OAuth login with session initialization error

## [0.2.1.0] - 2026-03-28

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
- Comprehensive project documentation (API.md, ARCHITECTURE.md, CONTRIBUTING.md, SERVICES.md, FRONTEND.md)
- 44 tests covering user model, route protection, health endpoint, and path helpers

### Fixed
- `_safe_resolve` now resolves base path with `realpath` to handle symlinks (e.g. macOS `/tmp`)
- `not_configured` Zep status no longer falsely reports `degraded`
- Raw exceptions no longer leak on public `/health` endpoint
- Cross-user directory scans removed from SimulationRunner and ReportManager
- Missing `_register_sim_user` calls on prepare/start simulation paths
- Missing `_register_report_user` call on generate report path
- Incorrect loop variable in `get_simulation_history` user registration
- Ownership verification added to all read endpoints (simulation detail, actions, messages, agent detail)
- Bare `except` replaced with `except Exception` in simulation history
- OAuth token exchange failures now logged with exc_info
- SQLite `busy_timeout` pragma added for concurrent access reliability
- `_VALID_PROVIDERS` derived from PROVIDERS dict instead of hardcoded
- Test SECRET_KEY lengthened to satisfy 32-char minimum validation
- Removed 3 legacy unauthenticated fallback paths with latent path traversal risk
- App version in simulation history now read from pyproject.toml instead of hardcoded
- pyproject.toml version synced to 0.2.1.0
- Version test reads expected value from pyproject.toml dynamically
