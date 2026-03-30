"""
MiroFish Backend - Flask Application Factory
"""

import os
import time
import tomllib
import warnings
from datetime import datetime, timezone
from pathlib import Path

# Suppress multiprocessing resource_tracker warnings (from third-party libraries like transformers)
# Must be set before all other imports
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager

from .auth.oauth import init_oauth, validate_oauth_env
from .config import Config
from .db import init_db
from .utils.logger import setup_logger, get_logger

# Module-level limiter for import by blueprints
limiter = Limiter(
    get_remote_address,
    default_limits=["60 per minute"],
    storage_uri="memory://",
)


def create_app(config_class=Config):
    """Flask application factory function"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['_START_TIME'] = time.monotonic()

    # Set JSON encoding: ensure non-ASCII characters are displayed directly (not as \uXXXX)
    # Flask >= 2.3 uses app.json.ensure_ascii, older versions use JSON_AS_ASCII config
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # Set up logging
    logger = setup_logger('mirofish')
    
    # Only print startup info in the reloader subprocess (avoid printing twice in debug mode)
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish Backend starting...")
        logger.info("=" * 50)
    
    # Session configuration
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = not app.config.get('DEBUG', False)
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7 days

    # Rate limiting
    limiter.init_app(app)

    # Enable CORS
    frontend_origin = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    CORS(app, resources={r"/api/*": {"origins": [frontend_origin]}},
         supports_credentials=True)

    # Initialize database
    init_db()

    # OAuth env validation -- fail loudly if auth is on but creds are missing
    auth_enabled = os.environ.get('AUTH_ENABLED', 'false').lower() == 'true'
    if auth_enabled:
        validate_oauth_env()
        secret = app.config.get('SECRET_KEY', '')
        if len(secret) < 32:
            raise RuntimeError(
                "AUTH_ENABLED=true but SECRET_KEY is missing or too short "
                "(minimum 32 characters). "
                "Set a strong SECRET_KEY in your .env file. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
    else:
        if should_log_startup:
            logger.warning(
                "AUTH_ENABLED is false — all API endpoints are unauthenticated. "
                "Set AUTH_ENABLED=true and configure OAuth credentials for production use."
            )

    if not os.environ.get('SECRET_KEY'):
        if should_log_startup:
            logger.warning(
                "SECRET_KEY not set — using auto-generated key. "
                "Sessions will not survive server restarts. "
                "Set SECRET_KEY in .env for persistent sessions."
            )

    # Initialize OAuth providers
    registered_providers = init_oauth(app)
    if should_log_startup and registered_providers:
        logger.info(f"OAuth providers registered: {', '.join(sorted(registered_providers))}")

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        return User.get_by_id(user_id)
    
    # Register simulation process cleanup function (ensure all simulation processes are terminated on server shutdown)
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("Simulation process cleanup function registered")
    
    # Auth middleware -- default-deny for protected routes
    @app.before_request
    def require_auth():
        from flask_login import current_user
        if not os.environ.get('AUTH_ENABLED', 'false').lower() == 'true':
            return None
        # Let CORS preflight through so flask-cors can handle it
        if request.method == 'OPTIONS':
            return None
        if request.path == '/health' or request.path.startswith('/api/auth/'):
            return None
        if not current_user.is_authenticated:
            return jsonify({'error': 'authentication_required'}), 401

    # CSRF protection: require custom header on POST requests
    # PUT/PATCH/DELETE always trigger CORS preflight (non-simple methods), so
    # CORS + SameSite is sufficient. POST needs the extra check because HTML
    # forms can send cross-origin POSTs without preflight.
    @app.before_request
    def csrf_check():
        if request.method != 'POST':
            return None
        if request.path == '/health' or request.path.startswith('/api/auth/'):
            return None
        content_type = request.content_type or ''
        has_custom_header = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        is_json = 'application/json' in content_type
        # Note: multipart/form-data is NOT checked here because it is a
        # "simple" content type that HTML forms can send cross-origin
        # without triggering CORS preflight.  The frontend axios client
        # always sends X-Requested-With: XMLHttpRequest (even on multipart
        # uploads), so has_custom_header covers that case.
        if not (has_custom_header or is_json):
            return jsonify({'error': 'Missing required request header'}), 403

    # Request logging middleware
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"Request: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"Request body: {request.get_json(silent=True)}")

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '0'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            f"connect-src 'self' {frontend_origin}; "
            "frame-ancestors 'none'"
        )
        logger = get_logger('mirofish.request')
        logger.debug(f"Response: {response.status_code}")
        return response

    # Register blueprints
    from .api import auth_bp, graph_bp, simulation_bp, report_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    
    # Read version from pyproject.toml for /health
    pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
    try:
        with open(pyproject_path, 'rb') as f:
            app.config['_APP_VERSION'] = tomllib.load(f)['project']['version']
    except Exception:
        app.config['_APP_VERSION'] = 'unknown'

    # Health check
    @app.route('/health')
    def health():
        elapsed = time.monotonic() - app.config['_START_TIME']
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)

        zep_status = _check_zep()
        overall = 'degraded' if zep_status.get('status') == 'error' else 'ok'

        return {
            'status': overall,
            'service': 'MiroFish Backend',
            'uptime': {
                'seconds': round(elapsed),
                'human': f'{hours}h {minutes}m {seconds}s',
            },
            'version': app.config['_APP_VERSION'],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'dependencies': {
                'zep_cloud': zep_status,
            },
        }

    if should_log_startup:
        logger.info("MiroFish Backend startup complete")

    return app


_zep_cache = {'result': None, 'expires': 0.0}


def _check_zep():
    """Lightweight Zep Cloud connectivity check with 2s timeout and 30s cache."""
    now = time.monotonic()
    if _zep_cache['result'] is not None and now < _zep_cache['expires']:
        return _zep_cache['result']

    api_key = Config.ZEP_API_KEY
    if not api_key:
        result = {'status': 'not_configured'}
    else:
        try:
            from zep_cloud.client import Zep
            start = time.monotonic()
            client = Zep(api_key=api_key, timeout=2.0)
            client.graph.list_all(page_size=1)
            latency = round((time.monotonic() - start) * 1000)
            result = {'status': 'ok', 'latency_ms': latency}
        except Exception as e:
            get_logger('mirofish').warning('Zep connectivity check failed: %s', e)
            result = {'status': 'error', 'message': 'connectivity check failed'}

    _zep_cache['result'] = result
    _zep_cache['expires'] = now + 30.0
    return result

