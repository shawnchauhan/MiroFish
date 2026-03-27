"""
User model with Flask-Login integration and SQLite CRUD operations.
"""

import uuid
from datetime import datetime, timezone

from flask_login import UserMixin

from ..db import get_connection


class User(UserMixin):
    """User record backed by SQLite. Implements Flask-Login's UserMixin."""

    def __init__(self, id, provider, provider_id, email=None,
                 display_name=None, avatar_url=None,
                 created_at=None, last_login_at=None):
        self.id = id
        self.provider = provider
        self.provider_id = provider_id
        self.email = email
        self.display_name = display_name
        self.avatar_url = avatar_url
        self.created_at = created_at or _now()
        self.last_login_at = last_login_at or _now()

    def to_dict(self):
        return {
            'id': self.id,
            'provider': self.provider,
            'provider_id': self.provider_id,
            'email': self.email,
            'display_name': self.display_name,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at,
            'last_login_at': self.last_login_at,
        }

    # ---- CRUD class methods ------------------------------------------------

    @classmethod
    def create(cls, provider, provider_id, email=None, display_name=None,
               avatar_url=None, db_path=None):
        """Insert a new user and return the User instance."""
        now = _now()
        user_id = str(uuid.uuid4())
        conn = get_connection(db_path)
        try:
            conn.execute(
                "INSERT INTO users (id, provider, provider_id, email, "
                "display_name, avatar_url, created_at, last_login_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, provider, provider_id, email, display_name,
                 avatar_url, now, now),
            )
            conn.commit()
        finally:
            conn.close()
        return cls(user_id, provider, provider_id, email, display_name,
                   avatar_url, now, now)

    @classmethod
    def get_by_id(cls, user_id, db_path=None):
        """Fetch a user by primary key. Returns None if not found."""
        conn = get_connection(db_path)
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        finally:
            conn.close()
        return cls._from_row(row) if row else None

    @classmethod
    def get_by_provider(cls, provider, provider_id, db_path=None):
        """Fetch a user by provider identity. Returns None if not found."""
        conn = get_connection(db_path)
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE provider = ? AND provider_id = ?",
                (provider, provider_id),
            ).fetchone()
        finally:
            conn.close()
        return cls._from_row(row) if row else None

    @classmethod
    def upsert(cls, provider, provider_id, email=None, display_name=None,
               avatar_url=None, db_path=None):
        """Create or update a user on login. Returns the User instance.

        If the user already exists (same provider + provider_id), updates
        profile fields and last_login_at. Otherwise creates a new record.
        """
        existing = cls.get_by_provider(provider, provider_id, db_path)
        if existing:
            now = _now()
            conn = get_connection(db_path)
            try:
                conn.execute(
                    "UPDATE users SET email = ?, display_name = ?, "
                    "avatar_url = ?, last_login_at = ? WHERE id = ?",
                    (email, display_name, avatar_url, now, existing.id),
                )
                conn.commit()
            finally:
                conn.close()
            existing.email = email
            existing.display_name = display_name
            existing.avatar_url = avatar_url
            existing.last_login_at = now
            return existing
        return cls.create(provider, provider_id, email, display_name,
                          avatar_url, db_path)

    # ---- Internal helpers ---------------------------------------------------

    @classmethod
    def _from_row(cls, row):
        if row is None:
            return None
        return cls(
            id=row['id'],
            provider=row['provider'],
            provider_id=row['provider_id'],
            email=row['email'],
            display_name=row['display_name'],
            avatar_url=row['avatar_url'],
            created_at=row['created_at'],
            last_login_at=row['last_login_at'],
        )


def _now():
    return datetime.now(timezone.utc).isoformat()
