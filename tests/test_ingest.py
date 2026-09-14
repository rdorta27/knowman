from pathlib import Path

from conftest import requires_db

from knowman.embeddings.base import EmbeddingsProvider
from knowman.ingest import ingest_path


class FakeEmbeddings(EmbeddingsProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t))] + [0.0] * 767 for t in texts]


@requires_db
def test_ingest_path_is_idempotent(store, tmp_path: Path):
    note = tmp_path / "note.md"
    note.write_text("# Title\n\nSome content here.\n")

    first = ingest_path(tmp_path, store, FakeEmbeddings())
    second = ingest_path(tmp_path, store, FakeEmbeddings())

    assert first == second
    assert store.count_chunks() == first


@requires_db
def test_ingest_path_reads_every_markdown_file(store, tmp_path: Path):
    (tmp_path / "one.md").write_text("first\n")
    (tmp_path / "two.md").write_text("second\n")

    ingest_path(tmp_path, store, FakeEmbeddings())

    assert store.count_chunks() == 2
