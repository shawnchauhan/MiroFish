"""
Authlib OAuth client configuration for Google and GitHub providers.
"""

import os

from authlib.integrations.flask_client import OAuth

oauth = OAuth()

# Provider metadata ---------------------------------------------------------

PROVIDERS = {
    'google': {
        'client_id_env': 'GOOGLE_CLIENT_ID',
        'client_secret_env': 'GOOGLE_CLIENT_SECRET',
        'server_metadata_url': (
            'https://accounts.google.com/.well-known/openid-configuration'
        ),
        'client_kwargs': {'scope': 'openid email profile'},
    },
    'github': {
        'client_id_env': 'GITHUB_CLIENT_ID',
        'client_secret_env': 'GITHUB_CLIENT_SECRET',
        'api_base_url': 'https://api.github.com/',
        'access_token_url': 'https://github.com/login/oauth/access_token',
        'authorize_url': 'https://github.com/login/oauth/authorize',
        'client_kwargs': {'scope': 'read:user user:email'},
    },
}


def init_oauth(app):
    """Register OAuth providers on the Flask app.

    Only registers providers whose credentials are present in the
    environment. Returns the set of provider names that were registered.
    """
    oauth.init_app(app)
    registered = set()

    for name, meta in PROVIDERS.items():
        client_id = os.environ.get(meta['client_id_env'])
        client_secret = os.environ.get(meta['client_secret_env'])
        if not client_id or not client_secret:
            continue

        kwargs = {
            'client_id': client_id,
            'client_secret': client_secret,
            'client_kwargs': meta['client_kwargs'],
        }

        if 'server_metadata_url' in meta:
            kwargs['server_metadata_url'] = meta['server_metadata_url']
        else:
            kwargs['api_base_url'] = meta['api_base_url']
            kwargs['access_token_url'] = meta['access_token_url']
            kwargs['authorize_url'] = meta['authorize_url']

        oauth.register(name=name, **kwargs)
        registered.add(name)

    return registered


def validate_oauth_env():
    """Raise if AUTH_ENABLED=true but no provider credentials are set."""
    for name, meta in PROVIDERS.items():
        cid = os.environ.get(meta['client_id_env'])
        csec = os.environ.get(meta['client_secret_env'])
        if cid and csec:
            return  # at least one provider is configured
    raise RuntimeError(
        'AUTH_ENABLED is true but no OAuth provider credentials found. '
        'Set GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET or '
        'GITHUB_CLIENT_ID/GITHUB_CLIENT_SECRET in your .env file.'
    )
