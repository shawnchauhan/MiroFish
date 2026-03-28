"""
Auth blueprint -- OAuth2 login/callback, logout, status, and profile.

Mounted at ``/api/auth`` by the app factory.
"""

import os

from flask import Blueprint, jsonify, redirect, request, session, url_for
from flask_login import current_user, login_user, logout_user

from ..auth.oauth import oauth
from ..models.user import User

auth_bp = Blueprint('auth', __name__)

# Allowed OAuth providers (keep in sync with oauth.py PROVIDERS)
_VALID_PROVIDERS = {'google', 'github'}


def _auth_enabled():
    return os.environ.get('AUTH_ENABLED', 'false').lower() == 'true'


def _dev_user():
    """Return (and upsert) a deterministic dev user for local work."""
    return User.upsert(
        provider='dev',
        provider_id='dev-local-user',
        email='dev@localhost',
        display_name='Dev User',
    )


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@auth_bp.route('/login/<provider>')
def login(provider):
    """Redirect the browser to the OAuth provider's authorization page."""
    if not _auth_enabled():
        # In dev mode, just log in as the dev user directly
        user = _dev_user()
        login_user(user)
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        return redirect(frontend_url)

    if provider not in _VALID_PROVIDERS:
        return jsonify({'error': f'Unknown provider: {provider}'}), 400

    client = oauth.create_client(provider)
    if client is None:
        return jsonify({'error': f'Provider {provider} is not configured'}), 400

    callback_url = url_for('auth.callback', provider=provider, _external=True)
    return client.authorize_redirect(callback_url)


@auth_bp.route('/callback/<provider>')
def callback(provider):
    """Handle the OAuth callback, upsert the user, and redirect to the app."""
    if provider not in _VALID_PROVIDERS:
        return jsonify({'error': f'Unknown provider: {provider}'}), 400

    client = oauth.create_client(provider)
    if client is None:
        return jsonify({'error': f'Provider {provider} is not configured'}), 400

    # Exchange code for token -- Authlib validates the state parameter
    try:
        token = client.authorize_access_token()
    except Exception:
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        return redirect(f'{frontend_url}/login?auth_error=token_exchange_failed')

    # Fetch user profile from the provider
    if provider == 'google':
        user_info = token.get('userinfo') or client.userinfo()
        provider_id = user_info['sub']
        email = user_info.get('email')
        display_name = user_info.get('name')
        avatar_url = user_info.get('picture')
    else:  # github
        resp = client.get('user', token=token)
        user_info = resp.json()
        provider_id = str(user_info['id'])
        display_name = user_info.get('name') or user_info.get('login')
        avatar_url = user_info.get('avatar_url')
        # GitHub may not expose email publicly -- fetch from /user/emails
        email = user_info.get('email')
        if not email:
            emails_resp = client.get('user/emails', token=token)
            emails = emails_resp.json()
            primary = next(
                (e for e in emails if e.get('primary') and e.get('verified')),
                None,
            )
            email = primary['email'] if primary else None

    # Upsert and log in
    user = User.upsert(
        provider=provider,
        provider_id=provider_id,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
    )
    login_user(user)

    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    return redirect(frontend_url)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Clear the session and log out."""
    logout_user()
    session.clear()
    return jsonify({'message': 'Logged out'}), 200


@auth_bp.route('/status')
def status():
    """Return whether the user is authenticated."""
    if not _auth_enabled():
        return jsonify({
            'auth_enabled': False,
            'authenticated': True,
            'user': _dev_user().to_dict(),
        })

    if current_user.is_authenticated:
        return jsonify({
            'auth_enabled': True,
            'authenticated': True,
            'user': current_user.to_dict(),
        })

    return jsonify({
        'auth_enabled': True,
        'authenticated': False,
        'user': None,
    })


@auth_bp.route('/me')
def me():
    """Return the current user's profile. 401 if not logged in."""
    if not _auth_enabled():
        return jsonify(_dev_user().to_dict())

    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401

    return jsonify(current_user.to_dict())
