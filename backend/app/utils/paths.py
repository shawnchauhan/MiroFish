"""
User-scoped file path helpers with path traversal protection.

All file I/O must go through these helpers to ensure user isolation.
"""

import os

from ..config import Config

_UPLOAD_ROOT = os.path.realpath(Config.UPLOAD_FOLDER)


def _safe_resolve(base, *parts):
    """Resolve a path and verify it stays inside *base*.

    Raises ValueError on path traversal attempts.
    """
    base = os.path.realpath(base)
    joined = os.path.realpath(os.path.join(base, *parts))
    if not joined.startswith(base + os.sep) and joined != base:
        raise ValueError(f'Path traversal detected: {joined}')
    return joined


def _require_user_id(user_id):
    """Raise ValueError if user_id is empty/None."""
    if not user_id or not str(user_id).strip():
        raise ValueError('user_id must not be empty')


def user_upload_dir(user_id):
    """Root upload directory for a given user."""
    _require_user_id(user_id)
    return _safe_resolve(_UPLOAD_ROOT, user_id)


def user_projects_dir(user_id):
    """Projects directory: uploads/{user_id}/projects/"""
    _require_user_id(user_id)
    return _safe_resolve(_UPLOAD_ROOT, user_id, 'projects')


def user_simulations_dir(user_id):
    """Simulations directory: uploads/{user_id}/simulations/"""
    _require_user_id(user_id)
    return _safe_resolve(_UPLOAD_ROOT, user_id, 'simulations')


def user_run_states_dir(user_id):
    """Simulation run-state directory: uploads/{user_id}/run_states/"""
    _require_user_id(user_id)
    return _safe_resolve(_UPLOAD_ROOT, user_id, 'run_states')


def user_reports_dir(user_id):
    """Reports directory: uploads/{user_id}/reports/"""
    _require_user_id(user_id)
    return _safe_resolve(_UPLOAD_ROOT, user_id, 'reports')
