from pathlib import Path

from watchfiles import Change, watch

from knowman.store import Store


def enqueue_for_change(change_type: Change, path: Path, root: Path, store: Store) -> None:
    """Turn one filesystem event into a job, the same shape the worker
    already knows how to run (knowman.worker._HANDLERS)."""
    if not path.name.endswith(".md"):
        return
    if change_type in (Change.added, Change.modified):
        store.enqueue_job("ingest_path", {"path": str(path), "root": str(root)})
    elif change_type == Change.deleted:
        store.enqueue_job("delete_path", {"path": str(path.relative_to(root))})


def run_watcher(root: Path, store: Store) -> None:
    for changes in watch(root):
        for change_type, changed_path in changes:
            enqueue_for_change(change_type, Path(changed_path), root, store)
