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
