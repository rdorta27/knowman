from pathlib import Path

from conftest import requires_db

from knowman.config import Settings
from knowman.dashboard import build_file_list, build_status, files_on_disk
from knowman.store import Chunk


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_files_on_disk_finds_every_markdown_file(tmp_path: Path):
    (tmp_path / "a.md").write_text("a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text("b")
    (tmp_path / "notes.txt").write_text("ignored")

    assert files_on_disk(tmp_path) == ["a.md", "sub/b.md"]


def test_files_on_disk_returns_empty_for_a_missing_directory(tmp_path: Path):
    assert files_on_disk(tmp_path / "does-not-exist") == []


@requires_db
def test_build_file_list_marks_an_unindexed_file(store, tmp_path: Path):
    (tmp_path / "indexed.md").write_text("x")
    (tmp_path / "not-indexed.md").write_text("y")
    store.upsert_chunks([Chunk("indexed.md", "h1", 1, 1, "text", [0.0] * 768)])
    settings = _settings(corpus_path=str(tmp_path))

    entries = build_file_list(settings, store)

    by_path = {e["path"]: e for e in entries}
    assert by_path["indexed.md"] == {
        "path": "indexed.md",
        "chunks": 1,
        "indexed": True,
        "on_disk": True,
    }
    assert by_path["not-indexed.md"] == {
        "path": "not-indexed.md",
        "chunks": 0,
        "indexed": False,
        "on_disk": True,
    }


@requires_db
def test_build_file_list_includes_an_indexed_file_deleted_from_disk(store, tmp_path: Path):
    store.upsert_chunks([Chunk("gone.md", "h1", 1, 1, "text", [0.0] * 768)])
    settings = _settings(corpus_path=str(tmp_path))

    entries = build_file_list(settings, store)

    assert entries == [{"path": "gone.md", "chunks": 1, "indexed": True, "on_disk": False}]


@requires_db
def test_build_status_reports_disk_index_and_queue_counts(store, tmp_path: Path):
    (tmp_path / "a.md").write_text("x")
    (tmp_path / "b.md").write_text("y")
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "text", [0.0] * 768)])
    store.enqueue_job("ingest_path", {"path": "a"})
    settings = _settings(corpus_path=str(tmp_path), embeddings_model="test-model")

    status = build_status(settings, store)

    assert status["files_on_disk"] == 2
    assert status["files_indexed"] == 1
    assert status["chunks"] == 1
    assert status["embeddings_model"] == "test-model"
    assert status["jobs"] == {"pending": 1, "processing": 0, "failed": 0}
