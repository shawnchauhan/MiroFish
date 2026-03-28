"""
SQLite database connection and schema initialization.
"""

import os
import sqlite3

_DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
_DB_PATH = os.path.join(_DB_DIR, 'users.db')

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    provider        TEXT NOT NULL,
    provider_id     TEXT NOT NULL,
    email           TEXT,
    display_name    TEXT,
    avatar_url      TEXT,
    created_at      TEXT NOT NULL,
    last_login_at   TEXT NOT NULL,
    UNIQUE(provider, provider_id)
);
"""


def get_db_path():
    """Return the path to the SQLite database file."""
    return _DB_PATH


def get_connection(db_path=None):
    """Get a SQLite connection. Uses the default path if none provided.

    The caller is responsible for closing the connection.
    """
    path = db_path or _DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path=None):
    """Create the users table if it does not exist."""
    path = db_path or _DB_PATH
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    conn = get_connection(path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()
