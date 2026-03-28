"""
Tests for IDOR vulnerability fixes (GST-34).

Covers:
1. ProjectManager.find_project_by_graph_id ownership lookup
2. TaskManager user_id scoping
3. verify_owner fail-closed in SimulationRunner and ReportManager
4. Graph data/delete endpoint ownership checks
5. Report tool endpoint ownership checks
"""

import os
import json
import shutil
import tempfile
import threading
import unittest
from collections import OrderedDict
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.models.task import TaskManager, Task, TaskStatus
from app.models.project import ProjectManager, Project, ProjectStatus


class TestProjectManagerFindByGraphId(unittest.TestCase):
    """Test ProjectManager.find_project_by_graph_id ownership lookup."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._upload_patcher = patch(
            'app.models.project.Config.UPLOAD_FOLDER', self._tmpdir
        )
        self._upload_patcher.start()

    def tearDown(self):
        self._upload_patcher.stop()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _create_project_with_graph(self, user_id, graph_id):
        project = ProjectManager.create_project(user_id, 'Test Project')
        project.graph_id = graph_id
        ProjectManager.save_project(user_id, project)
        return project

    def test_find_own_graph(self):
        """Owner can find their graph."""
        self._create_project_with_graph('user-a', 'graph-123')
        result = ProjectManager.find_project_by_graph_id('user-a', 'graph-123')
        self.assertIsNotNone(result)
        self.assertEqual(result.graph_id, 'graph-123')

    def test_other_user_cannot_find_graph(self):
        """Another user cannot find someone else's graph."""
        self._create_project_with_graph('user-a', 'graph-123')
        result = ProjectManager.find_project_by_graph_id('user-b', 'graph-123')
        self.assertIsNone(result)

    def test_nonexistent_graph(self):
        """Returns None for a graph_id that doesn't exist."""
        self._create_project_with_graph('user-a', 'graph-123')
        result = ProjectManager.find_project_by_graph_id('user-a', 'graph-999')
        self.assertIsNone(result)

    def test_no_projects_dir(self):
        """Returns None when user has no projects directory."""
        result = ProjectManager.find_project_by_graph_id('nonexistent-user', 'graph-123')
        self.assertIsNone(result)

    def test_project_without_graph(self):
        """Projects without graph_id are skipped."""
        ProjectManager.create_project('user-no-graph', 'No Graph Project')
        result = ProjectManager.find_project_by_graph_id('user-no-graph', 'graph-123')
        self.assertIsNone(result)


class TestTaskManagerUserScoping(unittest.TestCase):
    """Test TaskManager user_id scoping."""

    def setUp(self):
        # Reset the singleton for test isolation
        TaskManager._instance = None
        self.tm = TaskManager()

    def tearDown(self):
        TaskManager._instance = None

    def test_create_task_stores_user_id(self):
        task_id = self.tm.create_task('test_type', user_id='user-a')
        task = self.tm.get_task(task_id)
        self.assertEqual(task.user_id, 'user-a')

    def test_create_task_no_user_id(self):
        task_id = self.tm.create_task('test_type')
        task = self.tm.get_task(task_id)
        self.assertIsNone(task.user_id)

    def test_get_task_filters_by_user(self):
        task_id = self.tm.create_task('test_type', user_id='user-a')
        # Owner can see it
        self.assertIsNotNone(self.tm.get_task(task_id, user_id='user-a'))
        # Other user cannot
        self.assertIsNone(self.tm.get_task(task_id, user_id='user-b'))

    def test_get_task_no_filter(self):
        """Without user_id filter, any task is returned."""
        task_id = self.tm.create_task('test_type', user_id='user-a')
        self.assertIsNotNone(self.tm.get_task(task_id))

    def test_get_task_legacy_no_user(self):
        """Tasks without user_id are visible to any user_id filter."""
        task_id = self.tm.create_task('test_type')
        self.assertIsNotNone(self.tm.get_task(task_id, user_id='user-b'))

    def test_list_tasks_filters_by_user(self):
        self.tm.create_task('type_a', user_id='user-a')
        self.tm.create_task('type_b', user_id='user-b')
        self.tm.create_task('type_c')  # legacy, no user

        tasks_a = self.tm.list_tasks(user_id='user-a')
        # user-a sees their task + legacy task
        self.assertEqual(len(tasks_a), 2)

        tasks_b = self.tm.list_tasks(user_id='user-b')
        # user-b sees their task + legacy task
        self.assertEqual(len(tasks_b), 2)

    def test_list_tasks_no_filter(self):
        """Without user_id, all tasks are returned."""
        self.tm.create_task('type_a', user_id='user-a')
        self.tm.create_task('type_b', user_id='user-b')
        all_tasks = self.tm.list_tasks()
        self.assertEqual(len(all_tasks), 2)

    def test_to_dict_includes_user_id(self):
        task_id = self.tm.create_task('test_type', user_id='user-a')
        task = self.tm.get_task(task_id)
        d = task.to_dict()
        self.assertEqual(d['user_id'], 'user-a')


class TestVerifyOwnerFailClosed(unittest.TestCase):
    """Test that verify_owner is fail-closed in both SimulationRunner and ReportManager."""

    def test_simulation_runner_none_user(self):
        from app.services.simulation_runner import SimulationRunner
        self.assertFalse(SimulationRunner.verify_owner('sim-1', None))

    def test_simulation_runner_empty_user(self):
        from app.services.simulation_runner import SimulationRunner
        self.assertFalse(SimulationRunner.verify_owner('sim-1', ''))

    def test_simulation_runner_unknown_owner(self):
        """When no owner is recorded, deny access."""
        from app.services.simulation_runner import SimulationRunner
        # Mock get_run_state to return None (no state on disk)
        with patch.object(SimulationRunner, 'get_run_state', return_value=None):
            # Clear registry to simulate eviction/unknown
            with SimulationRunner._user_registry_lock:
                SimulationRunner._user_registry.pop('sim-unknown', None)
            self.assertFalse(SimulationRunner.verify_owner('sim-unknown', 'user-a'))

    def test_simulation_runner_owner_match(self):
        from app.services.simulation_runner import SimulationRunner
        with patch.object(SimulationRunner, 'get_run_state', return_value=None):
            with SimulationRunner._user_registry_lock:
                SimulationRunner._user_registry['sim-owned'] = 'user-a'
            self.assertTrue(SimulationRunner.verify_owner('sim-owned', 'user-a'))
            # Cleanup
            with SimulationRunner._user_registry_lock:
                SimulationRunner._user_registry.pop('sim-owned', None)

    def test_simulation_runner_owner_mismatch(self):
        from app.services.simulation_runner import SimulationRunner
        with patch.object(SimulationRunner, 'get_run_state', return_value=None):
            with SimulationRunner._user_registry_lock:
                SimulationRunner._user_registry['sim-owned2'] = 'user-a'
            self.assertFalse(SimulationRunner.verify_owner('sim-owned2', 'user-b'))
            # Cleanup
            with SimulationRunner._user_registry_lock:
                SimulationRunner._user_registry.pop('sim-owned2', None)

    def test_report_manager_none_user(self):
        from app.services.report_agent import ReportManager
        self.assertFalse(ReportManager.verify_owner('rpt-1', None))

    def test_report_manager_empty_user(self):
        from app.services.report_agent import ReportManager
        self.assertFalse(ReportManager.verify_owner('rpt-1', ''))

    def test_report_manager_unknown_owner(self):
        from app.services.report_agent import ReportManager
        with patch.object(ReportManager, 'get_report', return_value=None):
            with ReportManager._user_registry_lock:
                ReportManager._user_registry.pop('rpt-unknown', None)
            self.assertFalse(ReportManager.verify_owner('rpt-unknown', 'user-a'))

    def test_report_manager_owner_match(self):
        from app.services.report_agent import ReportManager
        with patch.object(ReportManager, 'get_report', return_value=None):
            with ReportManager._user_registry_lock:
                ReportManager._user_registry['rpt-owned'] = 'user-a'
            self.assertTrue(ReportManager.verify_owner('rpt-owned', 'user-a'))
            with ReportManager._user_registry_lock:
                ReportManager._user_registry.pop('rpt-owned', None)


class TestGraphEndpointOwnership(unittest.TestCase):
    """Test that graph data/delete endpoints enforce ownership."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._env_patcher = patch.dict(os.environ, {
            'AUTH_ENABLED': 'false',
        })
        self._env_patcher.start()

        from app import create_app
        from app.config import Config

        class _TestConfig(Config):
            TESTING = True
            SECRET_KEY = 'test-secret-key-that-is-at-least-32-characters-long'
            UPLOAD_FOLDER = self._tmpdir
            ZEP_API_KEY = 'fake-zep-key'

        self.app = create_app(_TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        self._env_patcher.stop()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_graph_data_no_ownership(self):
        """GET /api/graph/data/<graph_id> returns 404 for unowned graph."""
        resp = self.client.get('/api/graph/data/graph-not-mine')
        self.assertEqual(resp.status_code, 404)

    def test_graph_delete_no_ownership(self):
        """DELETE /api/graph/delete/<graph_id> returns 404 for unowned graph."""
        resp = self.client.delete('/api/graph/delete/graph-not-mine')
        self.assertEqual(resp.status_code, 404)

    def test_graph_data_with_ownership(self):
        """GET /api/graph/data/<graph_id> succeeds for owned graph (mocked Zep)."""
        # Create a project with a graph_id for the dev user
        with patch('app.models.project.Config.UPLOAD_FOLDER', self._tmpdir):
            project = ProjectManager.create_project('dev-local-user', 'Test')
            project.graph_id = 'graph-owned'
            ProjectManager.save_project('dev-local-user', project)

        # Mock GraphBuilderService to avoid real Zep calls
        with patch('app.api.graph.GraphBuilderService') as MockBuilder:
            MockBuilder.return_value.get_graph_data.return_value = {'nodes': [], 'edges': []}
            resp = self.client.get('/api/graph/data/graph-owned')
            self.assertEqual(resp.status_code, 200)


class TestReportToolEndpointOwnership(unittest.TestCase):
    """Test that report tool endpoints enforce graph ownership."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._env_patcher = patch.dict(os.environ, {
            'AUTH_ENABLED': 'false',
        })
        self._env_patcher.start()

        from app import create_app
        from app.config import Config

        class _TestConfig(Config):
            TESTING = True
            SECRET_KEY = 'test-secret-key-that-is-at-least-32-characters-long'
            UPLOAD_FOLDER = self._tmpdir
            ZEP_API_KEY = 'fake-zep-key'

        self.app = create_app(_TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        self._env_patcher.stop()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_search_no_ownership(self):
        """POST /api/report/tools/search returns 404 for unowned graph."""
        resp = self.client.post('/api/report/tools/search',
                                json={'graph_id': 'not-mine', 'query': 'test'})
        self.assertEqual(resp.status_code, 404)

    def test_statistics_no_ownership(self):
        """POST /api/report/tools/statistics returns 404 for unowned graph."""
        resp = self.client.post('/api/report/tools/statistics',
                                json={'graph_id': 'not-mine'})
        self.assertEqual(resp.status_code, 404)


class TestDevUserIdFlowthrough(unittest.TestCase):
    """Verify auth-disabled mode (dev-local-user) still flows correctly."""

    def test_dev_user_not_falsy(self):
        """The dev user ID must not be falsy, or verify_owner will deny."""
        from app.auth.helpers import _DEV_USER_ID
        self.assertTrue(bool(_DEV_USER_ID))

    def test_get_current_user_id_returns_dev_user(self):
        """When AUTH_ENABLED=false, get_current_user_id returns the dev user."""
        with patch.dict(os.environ, {'AUTH_ENABLED': 'false'}):
            from app.auth.helpers import get_current_user_id
            uid = get_current_user_id()
            self.assertEqual(uid, 'dev-local-user')
            self.assertTrue(bool(uid))


if __name__ == '__main__':
    unittest.main()
