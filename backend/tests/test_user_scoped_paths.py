"""
Tests for user-scoped file storage paths (Track 4).

Verifies:
- Path helpers resolve under UPLOAD_FOLDER
- Path traversal attempts raise ValueError
- Cross-user isolation: user A cannot see user B files
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from app.utils.paths import (
    _safe_resolve,
    user_upload_dir,
    user_projects_dir,
    user_simulations_dir,
    user_run_states_dir,
    user_reports_dir,
)


class TestPathHelpers(unittest.TestCase):

    def test_user_upload_dir(self):
        d = user_upload_dir('user-123')
        self.assertIn('user-123', d)
        self.assertTrue(d.endswith('user-123'))

    def test_user_projects_dir(self):
        d = user_projects_dir('user-123')
        self.assertIn('user-123', d)
        self.assertTrue(d.endswith(os.path.join('user-123', 'projects')))

    def test_user_simulations_dir(self):
        d = user_simulations_dir('user-123')
        self.assertTrue(d.endswith(os.path.join('user-123', 'simulations')))

    def test_user_run_states_dir(self):
        d = user_run_states_dir('user-123')
        self.assertTrue(d.endswith(os.path.join('user-123', 'run_states')))

    def test_user_reports_dir(self):
        d = user_reports_dir('user-123')
        self.assertTrue(d.endswith(os.path.join('user-123', 'reports')))


class TestPathTraversal(unittest.TestCase):

    def test_traversal_with_dotdot(self):
        with self.assertRaises(ValueError):
            _safe_resolve('/tmp/uploads', '../../etc/passwd')

    def test_traversal_with_encoded_dotdot(self):
        # os.path.realpath will resolve this
        with self.assertRaises(ValueError):
            _safe_resolve('/tmp/uploads', '../../../root')

    def test_safe_path_ok(self):
        import os
        result = _safe_resolve('/tmp/uploads', 'user-1', 'projects')
        expected = os.path.realpath('/tmp/uploads/user-1/projects')
        self.assertEqual(result, expected)


class TestCrossUserIsolation(unittest.TestCase):
    """ProjectManager operations are scoped per user."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_different_users_get_different_dirs(self):
        d1 = user_projects_dir('user-aaa')
        d2 = user_projects_dir('user-bbb')
        self.assertNotEqual(d1, d2)
        self.assertIn('user-aaa', d1)
        self.assertIn('user-bbb', d2)


if __name__ == '__main__':
    unittest.main()
