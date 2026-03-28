"""
Auth helpers for getting the current user in API endpoints.
"""

import os

from flask_login import current_user


_DEV_USER_ID = 'dev-local-user'


def get_current_user_id():
    """Return the authenticated user's ID, or *None* if unauthenticated.

    When ``AUTH_ENABLED`` is false, returns a stable dev-user ID so that
    file-scoping still works consistently during local development.
    """
    auth_enabled = os.environ.get('AUTH_ENABLED', 'false').lower() == 'true'

    if not auth_enabled:
        return _DEV_USER_ID

    if not current_user.is_authenticated:
        return None

    return current_user.id
