import os
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from knowman.store import Store

_DEV_DATABASE_URL = "postgresql://knowman:knowman@localhost:5432/knowman"


def _default_test_database_url() -> str:
    """Point at a <dbname>_test database by default, never the dev one directly —
    tests truncate tables, and running them must not wipe a developer's local index."""
    parts = urlsplit(_DEV_DATABASE_URL)
    return urlunsplit(parts._replace(path=f"{parts.path}_test"))


_TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", _default_test_database_url())


def _ensure_test_database_exists() -> None:
    target = urlsplit(_TEST_DATABASE_URL)
    db_name = target.path.lstrip("/")
    admin_url = urlunsplit(target._replace(path="/postgres"))
    with psycopg.connect(admin_url, connect_timeout=1, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{db_name}"')


def _db_available() -> bool:
    try:
        _ensure_test_database_exists()
        with psycopg.connect(_TEST_DATABASE_URL, connect_timeout=1):
            return True
    except psycopg.OperationalError:
        return False


requires_db = pytest.mark.skipif(not _db_available(), reason="no Postgres reachable for tests")


@pytest.fixture
def store():
    s = Store(_TEST_DATABASE_URL)
    s.init_schema()
    with psycopg.connect(_TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute("TRUNCATE chunks, jobs RESTART IDENTITY")
    return s
