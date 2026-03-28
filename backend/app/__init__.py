"""
MiroFish Backend - Flask应用工厂
"""

import os
import time
import tomllib
import warnings
from datetime import datetime, timezone
from pathlib import Path

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
# 需要在所有其他导入之前设置
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_login import LoginManager

from .auth.oauth import init_oauth, validate_oauth_env
from .config import Config
from .db import init_db
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['_START_TIME'] = time.monotonic()

    # 设置JSON编码：确保中文直接显示（而不是 \uXXXX 格式）
    # Flask >= 2.3 使用 app.json.ensure_ascii，旧版本使用 JSON_AS_ASCII 配置
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # 设置日志
    logger = setup_logger('mirofish')
    
    # 只在 reloader 子进程中打印启动信息（避免 debug 模式下打印两次）
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish Backend 启动中...")
        logger.info("=" * 50)
    
    # Session configuration
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = not app.config.get('DEBUG', False)
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7 days

    # 启用CORS
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
        if secret == 'mirofish-secret-key' or len(secret) < 32:
            raise RuntimeError(
                "AUTH_ENABLED=true but SECRET_KEY is missing or too short "
                "(minimum 32 characters). "
                "Set a strong SECRET_KEY in your .env file. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
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
    
    # 注册模拟进程清理函数（确保服务器关闭时终止所有模拟进程）
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("已注册模拟进程清理函数")
    
    # Auth middleware -- default-deny for protected routes
    @app.before_request
    def require_auth():
        from flask_login import current_user
        if not os.environ.get('AUTH_ENABLED', 'false').lower() == 'true':
            return None
        if request.path == '/health' or request.path.startswith('/api/auth/'):
            return None
        if not current_user.is_authenticated:
            return jsonify({'error': 'authentication_required'}), 401

    # 请求日志中间件
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"请求: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"请求体: {request.get_json(silent=True)}")
    
    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"响应: {response.status_code}")
        return response
    
    # 注册蓝图
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

    # 健康检查
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
        logger.info("MiroFish Backend 启动完成")

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

