import time
from pathlib import Path

from knowman.embeddings.base import EmbeddingsProvider
from knowman.ingest import ingest_path
from knowman.store import Job, Store


def _run_ingest_path(job: Job, store: Store, embeddings: EmbeddingsProvider) -> None:
    path = Path(job.payload["path"])
    root = Path(job.payload["root"]) if "root" in job.payload else None
    ingest_path(path, store, embeddings, root=root)


def _run_delete_path(job: Job, store: Store, _embeddings: EmbeddingsProvider) -> None:
    store.delete_path(job.payload["path"])


_HANDLERS = {
    "ingest_path": _run_ingest_path,
    "delete_path": _run_delete_path,
}


def process_next_job(store: Store, embeddings: EmbeddingsProvider) -> bool:
    """Claim and run one pending job, if there is one. Returns whether it
    found work, so a caller can decide whether to keep polling immediately
    or wait."""
    job = store.claim_next_job()
    if job is None:
        return False

    handler = _HANDLERS.get(job.type)
    if handler is None:
        store.fail_job(job.id, f"unknown job type: {job.type!r}")
        return True

    try:
        handler(job, store, embeddings)
    except Exception as exc:
        store.fail_job(job.id, str(exc))
        return True

    store.complete_job(job.id)
    return True


def run_worker(store: Store, embeddings: EmbeddingsProvider, poll_interval: float = 2.0) -> None:
    while True:
        if not process_next_job(store, embeddings):
            time.sleep(poll_interval)
