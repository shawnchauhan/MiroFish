"""
Unit tests for User model with temporary SQLite database.
"""

import os
import sqlite3
import tempfile
import unittest

from app.db import get_connection, init_db
from app.models.user import User


class TestUserModel(unittest.TestCase):
    """Tests for User CRUD operations and Flask-Login integration."""

    def setUp(self):
        """Create a fresh temp database for each test."""
        self._tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        init_db(self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_create_user(self):
        user = User.create(
            provider="google",
            provider_id="g-123",
            email="alice@example.com",
            display_name="Alice",
            avatar_url="https://example.com/alice.png",
            db_path=self.db_path,
        )
        self.assertIsNotNone(user.id)
        self.assertEqual(user.provider, "google")
        self.assertEqual(user.provider_id, "g-123")
        self.assertEqual(user.email, "alice@example.com")
        self.assertEqual(user.display_name, "Alice")
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.last_login_at)

    def test_get_by_id(self):
        created = User.create(
            provider="github", provider_id="gh-1", db_path=self.db_path
        )
        fetched = User.get_by_id(created.id, db_path=self.db_path)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, created.id)
        self.assertEqual(fetched.provider, "github")

    def test_get_by_id_not_found(self):
        result = User.get_by_id("nonexistent-id", db_path=self.db_path)
        self.assertIsNone(result)

    def test_get_by_provider(self):
        User.create(
            provider="google", provider_id="g-42",
            email="bob@example.com", db_path=self.db_path,
        )
        fetched = User.get_by_provider("google", "g-42", db_path=self.db_path)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.email, "bob@example.com")

    def test_get_by_provider_not_found(self):
        result = User.get_by_provider("google", "nope", db_path=self.db_path)
        self.assertIsNone(result)

    def test_upsert_creates_new_user(self):
        user = User.upsert(
            provider="github",
            provider_id="gh-new",
            email="new@example.com",
            display_name="New User",
            db_path=self.db_path,
        )
        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, "new@example.com")

        # Verify in DB
        fetched = User.get_by_provider("github", "gh-new", db_path=self.db_path)
        self.assertEqual(fetched.id, user.id)

    def test_upsert_updates_existing_user(self):
        original = User.create(
            provider="google",
            provider_id="g-99",
            email="old@example.com",
            display_name="Old Name",
            db_path=self.db_path,
        )
        original_login = original.last_login_at

        updated = User.upsert(
            provider="google",
            provider_id="g-99",
            email="new@example.com",
            display_name="New Name",
            avatar_url="https://example.com/new.png",
            db_path=self.db_path,
        )

        # Same user ID
        self.assertEqual(updated.id, original.id)
        # Updated fields
        self.assertEqual(updated.email, "new@example.com")
        self.assertEqual(updated.display_name, "New Name")
        self.assertEqual(updated.avatar_url, "https://example.com/new.png")
        # last_login_at should be updated
        self.assertGreaterEqual(updated.last_login_at, original_login)

        # Verify in DB
        fetched = User.get_by_id(original.id, db_path=self.db_path)
        self.assertEqual(fetched.email, "new@example.com")

    def test_unique_constraint_on_provider(self):
        """Two users with same (provider, provider_id) should fail on direct insert."""
        User.create(
            provider="github", provider_id="gh-dup", db_path=self.db_path
        )
        with self.assertRaises(sqlite3.IntegrityError):
            User.create(
                provider="github", provider_id="gh-dup", db_path=self.db_path
            )

    def test_different_providers_same_provider_id(self):
        """Same provider_id from different providers should be separate users."""
        google_user = User.create(
            provider="google", provider_id="shared-id", db_path=self.db_path
        )
        github_user = User.create(
            provider="github", provider_id="shared-id", db_path=self.db_path
        )
        self.assertNotEqual(google_user.id, github_user.id)

    def test_to_dict(self):
        user = User.create(
            provider="google",
            provider_id="g-dict",
            email="dict@example.com",
            display_name="Dict User",
            db_path=self.db_path,
        )
        d = user.to_dict()
        self.assertEqual(d['id'], user.id)
        self.assertEqual(d['provider'], "google")
        self.assertEqual(d['email'], "dict@example.com")
        self.assertIn('created_at', d)
        self.assertIn('last_login_at', d)

    def test_flask_login_interface(self):
        """User must satisfy Flask-Login's UserMixin interface."""
        user = User.create(
            provider="google", provider_id="g-login", db_path=self.db_path
        )
        self.assertTrue(user.is_authenticated)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_anonymous)
        self.assertEqual(user.get_id(), user.id)

    def test_nullable_email(self):
        """GitHub users may have no public email."""
        user = User.create(
            provider="github", provider_id="gh-noemail", db_path=self.db_path
        )
        self.assertIsNone(user.email)
        fetched = User.get_by_id(user.id, db_path=self.db_path)
        self.assertIsNone(fetched.email)


if __name__ == "__main__":
    unittest.main()
