"""Assembles the read-only data the monitoring panel shows: what's on disk,
what's indexed, and how the queue looks. Kept out of api.py the same way
ask.py keeps ask's logic out of it — the routes stay thin calls into here."""

from pathlib import Path

from knowman.config import Settings
from knowman.store import Store


def files_on_disk(corpus_path: Path) -> list[str]:
    """Every .md file under corpus_path, as paths relative to it — the same
    shape ingest_path already uses, so a path here matches a path in chunks."""
    if not corpus_path.is_dir():
        return []
    return sorted(str(p.relative_to(corpus_path)) for p in corpus_path.rglob("*.md"))


def build_status(settings: Settings, store: Store) -> dict:
    on_disk = files_on_disk(Path(settings.corpus_path))
    indexed = store.chunk_counts_by_path()
    jobs_by_status = store.count_jobs_by_status()
    return {
        "files_on_disk": len(on_disk),
        "files_indexed": len(indexed),
        "chunks": sum(indexed.values()),
        "embeddings_model": settings.embeddings_model,
        "jobs": {
            "pending": jobs_by_status.get("pending", 0),
            "processing": jobs_by_status.get("processing", 0),
            "failed": jobs_by_status.get("failed", 0),
        },
    }


def build_file_list(settings: Settings, store: Store) -> list[dict]:
    """One entry per file that's on disk, indexed, or both. on_disk and
    indexed are tracked separately (not folded into one status) so a file
    indexed but deleted since its last ingest — a stale citation waiting to
    happen — is distinguishable from an ordinary indexed file, which
    "indexed": True alone can't tell apart."""
    on_disk = set(files_on_disk(Path(settings.corpus_path)))
    indexed = store.chunk_counts_by_path()
    every_path = sorted(on_disk | indexed.keys())
    return [
        {
            "path": path,
            "chunks": indexed.get(path, 0),
            "indexed": path in indexed,
            "on_disk": path in on_disk,
        }
        for path in every_path
    ]
