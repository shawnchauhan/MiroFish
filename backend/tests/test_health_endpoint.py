"""
Tests for the enhanced /health endpoint.
"""

import re
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app import create_app


class TestHealthEndpoint(unittest.TestCase):
    """Tests for /health response shape, backward compat, and dependency checks."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_returns_200(self):
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)

    def test_backward_compat_fields(self):
        data = self.client.get('/health').get_json()
        self.assertIn('status', data)
        self.assertIn('service', data)
        self.assertEqual(data['service'], 'MiroFish Backend')

    def test_uptime_is_positive(self):
        data = self.client.get('/health').get_json()
        self.assertIn('uptime', data)
        self.assertIsInstance(data['uptime']['seconds'], int)
        self.assertGreaterEqual(data['uptime']['seconds'], 0)

    def test_uptime_human_format(self):
        data = self.client.get('/health').get_json()
        human = data['uptime']['human']
        self.assertRegex(human, r'^\d+h \d+m \d+s$')

    def test_version_matches_pyproject(self):
        data = self.client.get('/health').get_json()
        self.assertEqual(data['version'], '0.1.0')

    def test_timestamp_is_valid_iso8601(self):
        data = self.client.get('/health').get_json()
        ts = data['timestamp']
        parsed = datetime.fromisoformat(ts)
        self.assertIsNotNone(parsed.tzinfo)

    def test_dependencies_zep_cloud_present(self):
        data = self.client.get('/health').get_json()
        self.assertIn('dependencies', data)
        self.assertIn('zep_cloud', data['dependencies'])
        zep = data['dependencies']['zep_cloud']
        self.assertIn('status', zep)
        self.assertIn(zep['status'], ('ok', 'error', 'not_configured'))

    @patch('app.Config')
    def test_zep_not_configured_when_no_key(self, mock_config):
        from app import _check_zep
        mock_config.ZEP_API_KEY = ''
        result = _check_zep()
        self.assertEqual(result['status'], 'not_configured')

    @patch('app._check_zep')
    def test_overall_status_ok_when_zep_ok(self, mock_zep):
        mock_zep.return_value = {'status': 'ok', 'latency_ms': 100}
        data = self.client.get('/health').get_json()
        self.assertEqual(data['status'], 'ok')

    @patch('app._check_zep')
    def test_overall_status_degraded_when_zep_error(self, mock_zep):
        mock_zep.return_value = {'status': 'error', 'message': 'connection refused'}
        data = self.client.get('/health').get_json()
        self.assertEqual(data['status'], 'degraded')

    @patch('app._check_zep')
    def test_overall_status_degraded_when_zep_not_configured(self, mock_zep):
        mock_zep.return_value = {'status': 'not_configured'}
        data = self.client.get('/health').get_json()
        self.assertEqual(data['status'], 'degraded')

    def test_health_accessible_without_auth(self):
        """Health endpoint must be accessible even with AUTH_ENABLED=true."""
        with patch.dict('os.environ', {'AUTH_ENABLED': 'true', 'SECRET_KEY': 'test-secret-key-long-enough'}):
            resp = self.client.get('/health')
            self.assertEqual(resp.status_code, 200)

    def test_all_required_fields_present(self):
        data = self.client.get('/health').get_json()
        required = ['status', 'service', 'uptime', 'version', 'timestamp', 'dependencies']
        for field in required:
            self.assertIn(field, data, f"Missing required field: {field}")


if __name__ == '__main__':
    unittest.main()
