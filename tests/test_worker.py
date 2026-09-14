from pathlib import Path

from conftest import requires_db

from knowman.embeddings.base import EmbeddingsProvider
from knowman.store import Chunk
from knowman.worker import process_next_job


class FakeEmbeddings(EmbeddingsProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 768 for _ in texts]


@requires_db
def test_process_next_job_runs_ingest_path_and_marks_it_done(store, tmp_path: Path):
    (tmp_path / "note.md").write_text("some content\n")
    job_id = store.enqueue_job("ingest_path", {"path": str(tmp_path)})

    found_work = process_next_job(store, FakeEmbeddings())

    assert found_work is True
    assert store.get_job(job_id).status == "done"
    assert store.count_chunks() == 1


@requires_db
def test_process_next_job_runs_delete_path(store):
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "text", [0.0] * 768)])
    job_id = store.enqueue_job("delete_path", {"path": "a.md"})

    process_next_job(store, FakeEmbeddings())

    assert store.get_job(job_id).status == "done"
    assert store.count_chunks() == 0


@requires_db
def test_process_next_job_marks_a_failing_job_failed(store):
    job_id = store.enqueue_job("ingest_path", {"path": "/does/not/exist.md"})

    process_next_job(store, FakeEmbeddings())

    assert store.get_job(job_id).status == "failed"
    assert store.get_job(job_id).error


@requires_db
def test_process_next_job_returns_false_when_no_jobs_are_pending(store):
    assert process_next_job(store, FakeEmbeddings()) is False
