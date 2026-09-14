from pathlib import Path

from conftest import requires_db
from watchfiles import Change

from knowman.watcher import enqueue_for_change


@requires_db
def test_enqueue_for_change_added_enqueues_ingest_path(store):
    root = Path("/watched")
    enqueue_for_change(Change.added, root / "note.md", root, store)

    job = store.claim_next_job()
    assert job.type == "ingest_path"
    assert job.payload == {"path": "/watched/note.md", "root": "/watched"}


@requires_db
def test_enqueue_for_change_deleted_enqueues_delete_path(store):
    root = Path("/watched")
    enqueue_for_change(Change.deleted, root / "note.md", root, store)

    job = store.claim_next_job()
    assert job.type == "delete_path"
    assert job.payload == {"path": "note.md"}


@requires_db
def test_enqueue_for_change_ignores_non_markdown_files(store):
    root = Path("/watched")
    enqueue_for_change(Change.added, root / "note.txt", root, store)

    assert store.claim_next_job() is None
