from pathlib import Path

import pytest
from conftest import _TEST_DATABASE_URL, requires_db

import knowman.agent as agent_module
from knowman.agent import UnsafeNotePathError, _resolve_note_path, search_notes, write_note
from knowman.embeddings.base import EmbeddingsProvider
from knowman.store import Chunk

_NEAR = [1.0, 0.0, 0.0] + [0.0] * 765


class FixedEmbeddings(EmbeddingsProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_NEAR for _ in texts]


def test_resolve_note_path_accepts_a_safe_filename(tmp_path: Path):
    resolved = _resolve_note_path("note.md", tmp_path)
    assert resolved == (tmp_path / "note.md").resolve()


@pytest.mark.parametrize("filename", ["../escape.md", "/etc/passwd", "../../etc/passwd"])
def test_resolve_note_path_rejects_paths_escaping_the_corpus(tmp_path: Path, filename: str):
    with pytest.raises(UnsafeNotePathError):
        _resolve_note_path(filename, tmp_path)


@requires_db
def test_write_note_writes_and_indexes_the_file(store, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setenv("CORPUS_PATH", str(tmp_path))
    monkeypatch.setattr(agent_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())

    result = write_note.invoke({"filename": "meeting.md", "content": "we decided X"})

    assert "meeting.md" in result
    assert (tmp_path / "meeting.md").read_text() == "we decided X"
    assert store.count_chunks() == 1


@requires_db
def test_write_note_rejects_an_escaping_filename(store, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setenv("CORPUS_PATH", str(tmp_path))

    with pytest.raises(UnsafeNotePathError):
        write_note.invoke({"filename": "../escape.md", "content": "nope"})


@requires_db
def test_search_notes_returns_citations_for_a_matching_query(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setattr(agent_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "matching text", _NEAR)])

    result = search_notes.invoke({"query": "anything"})

    assert "a.md" in result
