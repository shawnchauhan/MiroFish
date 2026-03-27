"""
Integration tests for route protection middleware (Track 3).

Tests verify that:
- Protected routes return 401 when unauthenticated and AUTH_ENABLED=true
- Public routes (/health, /api/auth/*) are accessible without auth
- All routes are accessible when AUTH_ENABLED=false
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from app.config import Config
from app.db import init_db


class _TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret'


class TestRouteProtectionAuthEnabled(unittest.TestCase):
    """Routes should require auth when AUTH_ENABLED=true."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        init_db(self.db_path)

        env = {
            'AUTH_ENABLED': 'true',
            # Provide dummy creds so validate_oauth_env doesn't raise
            'GOOGLE_CLIENT_ID': 'fake-id',
            'GOOGLE_CLIENT_SECRET': 'fake-secret',
        }
        with patch.dict(os.environ, env):
            self.app = create_app(_TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.db_path)

    def test_health_is_public(self):
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)

    def test_auth_status_is_public(self):
        resp = self.client.get('/api/auth/status')
        self.assertEqual(resp.status_code, 200)

    def test_auth_login_is_public(self):
        # Will return 400 (unknown provider) but NOT 401
        resp = self.client.get('/api/auth/login/google')
        self.assertNotEqual(resp.status_code, 401)

    def test_graph_requires_auth(self):
        resp = self.client.get('/api/graph/anything')
        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertEqual(data['error'], 'authentication_required')

    def test_simulation_requires_auth(self):
        resp = self.client.get('/api/simulation/anything')
        self.assertEqual(resp.status_code, 401)

    def test_report_requires_auth(self):
        resp = self.client.get('/api/report/anything')
        self.assertEqual(resp.status_code, 401)


class TestRouteProtectionAuthDisabled(unittest.TestCase):
    """All routes should be accessible when AUTH_ENABLED=false."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        init_db(self.db_path)

        env = {'AUTH_ENABLED': 'false'}
        with patch.dict(os.environ, env):
            self.app = create_app(_TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.db_path)

    def test_health_accessible(self):
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)

    def test_graph_accessible_without_auth(self):
        # May return 404 (no matching sub-route), but NOT 401
        resp = self.client.get('/api/graph/anything')
        self.assertNotEqual(resp.status_code, 401)

    def test_auth_status_returns_dev_user(self):
        resp = self.client.get('/api/auth/status')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['auth_enabled'])
        self.assertTrue(data['authenticated'])
        self.assertEqual(data['user']['provider'], 'dev')


if __name__ == '__main__':
    unittest.main()
