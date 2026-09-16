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


@requires_db
def test_list_recent_jobs_orders_newest_first_and_respects_limit(store):
    ids = [store.enqueue_job("ingest_path", {"path": str(i)}) for i in range(3)]

    jobs = store.list_recent_jobs(limit=2)

    assert [j.id for j in jobs] == [ids[2], ids[1]]


@requires_db
def test_list_recent_jobs_carries_status_and_error(store):
    job_id = store.enqueue_job("ingest_path", {"path": "a"})
    store.fail_job(job_id, "boom")

    (job,) = store.list_recent_jobs()

    assert job.status == "failed"
    assert job.error == "boom"


@requires_db
def test_count_jobs_by_status_groups_correctly(store):
    done_id = store.enqueue_job("ingest_path", {"path": "a"})
    failed_id = store.enqueue_job("ingest_path", {"path": "b"})
    store.enqueue_job("ingest_path", {"path": "c"})
    store.complete_job(done_id)
    store.fail_job(failed_id, "boom")

    counts = store.count_jobs_by_status()

    assert counts == {"done": 1, "failed": 1, "pending": 1}


@requires_db
def test_chunk_counts_by_path_groups_correctly(store):
    vector = [0.0] * 768
    store.upsert_chunks(
        [
            Chunk("a.md", "h1", 1, 1, "one", vector),
            Chunk("a.md", "h2", 2, 2, "two", vector),
            Chunk("b.md", "h3", 1, 1, "three", vector),
        ]
    )

    assert store.chunk_counts_by_path() == {"a.md": 2, "b.md": 1}


@requires_db
def test_list_traces_orders_newest_first_and_respects_limit(store):
    for query in ["q1", "q2", "q3"]:
        store.record_trace(
            prompt_id=None,
            query=query,
            citation_count=0,
            has_citation=False,
            latency_ms=1.0,
            tokens_approx=1,
            answered=False,
        )

    traces = store.list_traces(limit=2)

    assert [t.query for t in traces] == ["q3", "q2"]
