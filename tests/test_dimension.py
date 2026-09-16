import psycopg
from conftest import _TEST_DATABASE_URL, requires_db

from knowman.embeddings import detect_dimension
from knowman.embeddings.base import EmbeddingsProvider
from knowman.store import Store


class FakeEmbeddings(EmbeddingsProvider):
    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self._dimension for _ in texts]


def test_detect_dimension_returns_the_vector_length():
    assert detect_dimension(FakeEmbeddings(dimension=1024)) == 1024


@requires_db
def test_init_schema_creates_chunks_at_the_given_dimension():
    with psycopg.connect(_TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS chunks")
    Store(_TEST_DATABASE_URL).init_schema(dimension=5)
    with psycopg.connect(_TEST_DATABASE_URL) as conn:
        row = conn.execute("""
            SELECT atttypmod FROM pg_attribute
            WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'
            """).fetchone()
    assert row[0] == 5


@requires_db
def test_init_schema_creates_an_hnsw_index_on_the_embedding_column():
    with psycopg.connect(_TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS chunks")
    Store(_TEST_DATABASE_URL).init_schema(dimension=5)
    with psycopg.connect(_TEST_DATABASE_URL) as conn:
        row = conn.execute("""
            SELECT indexdef FROM pg_indexes
            WHERE tablename = 'chunks' AND indexname = 'chunks_embedding_idx'
            """).fetchone()
    assert row is not None
    assert "hnsw" in row[0]
    assert "vector_cosine_ops" in row[0]
