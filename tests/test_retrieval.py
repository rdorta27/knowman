from conftest import requires_db

from knowman.embeddings.base import EmbeddingsProvider
from knowman.retrieval import search
from knowman.store import Chunk

_NEAR = [1.0, 0.0, 0.0] + [0.0] * 765
_FAR = [0.0, 1.0, 0.0] + [0.0] * 765


class FixedEmbeddings(EmbeddingsProvider):
    def __init__(self, vector: list[float]) -> None:
        self._vector = vector

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector for _ in texts]


@requires_db
def test_search_keeps_results_within_the_distance_threshold(store):
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "near text", _NEAR)])
    citations = search("query", store, FixedEmbeddings(_NEAR), k=3, max_distance=0.01)
    assert len(citations) == 1
    assert citations[0].path == "a.md"


@requires_db
def test_search_drops_results_past_the_distance_threshold(store):
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "unrelated text", _FAR)])
    citations = search("query", store, FixedEmbeddings(_NEAR), k=3, max_distance=0.01)
    assert citations == []


@requires_db
def test_search_respects_k(store):
    store.upsert_chunks(
        [
            Chunk("a.md", "h1", 1, 1, "one", _NEAR),
            Chunk("b.md", "h2", 1, 1, "two", _NEAR),
            Chunk("c.md", "h3", 1, 1, "three", _NEAR),
        ]
    )
    citations = search("query", store, FixedEmbeddings(_NEAR), k=2, max_distance=1.0)
    assert len(citations) == 2
