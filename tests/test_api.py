from conftest import _TEST_DATABASE_URL, requires_db
from fastapi.testclient import TestClient

import knowman.api as api_module
from knowman.embeddings.base import EmbeddingsProvider
from knowman.store import Chunk

_NEAR = [1.0, 0.0, 0.0] + [0.0] * 765


class FixedEmbeddings(EmbeddingsProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_NEAR for _ in texts]


@requires_db
def test_health_reports_ok():
    client = TestClient(api_module.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@requires_db
def test_search_returns_citations_for_a_matching_query(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setattr(api_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "matching text", _NEAR)])

    client = TestClient(api_module.app)
    response = client.get("/search", params={"q": "anything"})

    assert response.status_code == 200
    citations = response.json()["citations"]
    assert len(citations) == 1
    assert citations[0]["path"] == "a.md"


@requires_db
def test_search_returns_empty_citations_for_an_out_of_corpus_query(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    far = [0.0, 1.0, 0.0] + [0.0] * 765
    monkeypatch.setattr(api_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "unrelated", far)])

    client = TestClient(api_module.app)
    response = client.get("/search", params={"q": "anything"})

    assert response.status_code == 200
    assert response.json()["citations"] == []
