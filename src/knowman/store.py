from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "001_init.sql"


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


@dataclass(frozen=True)
class Chunk:
    path: str
    content_hash: str
    line_start: int
    line_end: int
    text: str
    embedding: list[float]


@dataclass(frozen=True)
class Job:
    id: int
    type: str
    status: str
    payload: dict
    error: str | None


class Store:
    """The only module that speaks SQL to Postgres+pgvector.

    Swapping the vector engine later means rewriting this module, not the
    rest of the codebase (ki/project/archive/explorations/v0.1.0-1.md)."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def init_schema(self, dimension: int) -> None:
        """dimension comes from the configured embeddings provider (see
        knowman.embeddings.detect_dimension) — the chunks table's vector
        width depends on the model, not a fixed constant."""
        dimension = int(dimension)
        sql = _SCHEMA_PATH.read_text()
        with psycopg.connect(self._database_url, autocommit=True) as conn:
            conn.execute(sql)
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    id BIGSERIAL PRIMARY KEY,
                    path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding VECTOR({dimension}) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE (path, line_start, line_end)
                )
                """)
            conn.execute("CREATE INDEX IF NOT EXISTS chunks_path_idx ON chunks (path)")

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        """Insert chunks, replacing any existing ones for the same paths.
        A path's old chunks are dropped first so a shrunk file loses its
        stale, orphaned fragments instead of keeping dead citations."""
        if not chunks:
            return 0
        paths = {chunk.path for chunk in chunks}
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chunks WHERE path = ANY(%s)", (list(paths),))
                for chunk in chunks:
                    cur.execute(
                        """
                        INSERT INTO chunks
                            (path, content_hash, line_start, line_end, text, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (path, line_start, line_end) DO UPDATE SET
                            content_hash = EXCLUDED.content_hash,
                            text = EXCLUDED.text,
                            embedding = EXCLUDED.embedding
                        """,
                        (
                            chunk.path,
                            chunk.content_hash,
                            chunk.line_start,
                            chunk.line_end,
                            chunk.text,
                            chunk.embedding,
                        ),
                    )
            conn.commit()
        return len(chunks)

    def search(self, embedding: list[float], k: int = 5) -> list[dict]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT path, line_start, line_end, text, embedding <=> %s::vector AS distance
                FROM chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (_vector_literal(embedding), _vector_literal(embedding), k),
            ).fetchall()
        return list(rows)

    def count_chunks(self) -> int:
        with psycopg.connect(self._database_url) as conn:
            return conn.execute("SELECT count(*) FROM chunks").fetchone()[0]

    def delete_path(self, path: str) -> None:
        with psycopg.connect(self._database_url, autocommit=True) as conn:
            conn.execute("DELETE FROM chunks WHERE path = %s", (path,))

    def enqueue_job(self, job_type: str, payload: dict) -> int:
        with psycopg.connect(self._database_url) as conn:
            row = conn.execute(
                "INSERT INTO jobs (type, payload) VALUES (%s, %s) RETURNING id",
                (job_type, psycopg.types.json.Json(payload)),
            ).fetchone()
            conn.commit()
        return row[0]

    def get_job(self, job_id: int) -> Job | None:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "SELECT id, type, status, payload, error FROM jobs WHERE id = %s", (job_id,)
            ).fetchone()
        return Job(**row) if row else None

    def claim_next_job(self) -> Job | None:
        """Atomically pick the oldest pending job and mark it processing, so
        a single worker (today) or several (later) never race the same row."""
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute("""
                UPDATE jobs SET status = 'processing', updated_at = now()
                WHERE id = (
                    SELECT id FROM jobs WHERE status = 'pending'
                    ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED
                )
                RETURNING id, type, status, payload, error
                """).fetchone()
            conn.commit()
        return Job(**row) if row else None

    def complete_job(self, job_id: int) -> None:
        with psycopg.connect(self._database_url, autocommit=True) as conn:
            conn.execute(
                "UPDATE jobs SET status = 'done', updated_at = now() WHERE id = %s", (job_id,)
            )

    def fail_job(self, job_id: int, error: str) -> None:
        with psycopg.connect(self._database_url, autocommit=True) as conn:
            conn.execute(
                "UPDATE jobs SET status = 'failed', error = %s, updated_at = now() WHERE id = %s",
                (error, job_id),
            )
