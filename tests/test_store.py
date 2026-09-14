from conftest import requires_db

from knowman.store import Chunk


@requires_db
def test_upsert_chunks_then_search_finds_the_closest(store):
    store.upsert_chunks(
        [
            Chunk("a.md", "h1", 1, 1, "near", [1.0, 0.0, 0.0] + [0.0] * 765),
            Chunk("b.md", "h2", 1, 1, "far", [0.0, 1.0, 0.0] + [0.0] * 765),
        ]
    )
    results = store.search([1.0, 0.0, 0.0] + [0.0] * 765, k=1)
    assert results[0]["path"] == "a.md"


@requires_db
def test_upsert_chunks_replaces_a_path_stale_chunks(store):
    vector = [0.0] * 768
    store.upsert_chunks([Chunk("a.md", "h1", 1, 5, "old", vector)])
    store.upsert_chunks([Chunk("a.md", "h2", 1, 2, "new", vector)])
    assert store.count_chunks() == 1


@requires_db
def test_enqueue_job_inserts_a_row(store):
    job_id = store.enqueue_job("ingest", {"path": "corpus/dummy"})
    assert job_id > 0


@requires_db
def test_delete_path_removes_only_the_targeted_path(store):
    vector = [0.0] * 768
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "keep this one", vector)])
    store.upsert_chunks([Chunk("b.md", "h2", 1, 1, "delete this one", vector)])

    store.delete_path("b.md")

    assert store.count_chunks() == 1


@requires_db
def test_claim_next_job_marks_it_processing_and_skips_it_next_time(store):
    job_id = store.enqueue_job("ingest_path", {"path": "corpus/dummy"})

    claimed = store.claim_next_job()

    assert claimed.id == job_id
    assert claimed.status == "processing"
    assert store.claim_next_job() is None


@requires_db
def test_complete_job_and_fail_job_set_status(store):
    done_id = store.enqueue_job("ingest_path", {"path": "a"})
    failed_id = store.enqueue_job("ingest_path", {"path": "b"})

    store.complete_job(done_id)
    store.fail_job(failed_id, "boom")

    assert store.get_job(done_id).status == "done"
    failed = store.get_job(failed_id)
    assert failed.status == "failed"
    assert failed.error == "boom"
