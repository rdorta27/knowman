import os

import psycopg
import pytest

from knowman.store import Store

_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://knowman:knowman@localhost:5432/knowman"
)


def _db_available() -> bool:
    try:
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
