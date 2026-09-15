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


@requires_db
def test_index_then_get_reflects_job_status(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)

    client = TestClient(api_module.app)
    post_response = client.post("/index")
    assert post_response.status_code == 202
    job_id = post_response.json()["job_id"]

    get_response = client.get(f"/index/{job_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "pending"

    store.complete_job(job_id)
    assert client.get(f"/index/{job_id}").json()["status"] == "done"


@requires_db
def test_get_index_job_hides_the_raw_exception_on_failure(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    job_id = store.enqueue_job("ingest_path", {"path": "/nope"})
    store.fail_job(job_id, "Traceback: /home/someone/secret/path.py line 42")

    client = TestClient(api_module.app)
    response = client.get(f"/index/{job_id}")

    assert response.json()["error"] == "job failed"
    assert store.get_job(job_id).error == "Traceback: /home/someone/secret/path.py line 42"


@requires_db
def test_ask_with_no_provider_returns_citations_and_null_answer(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setattr(api_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())
    monkeypatch.setattr(api_module, "get_llm_provider", lambda settings: None)
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "matching text", _NEAR)])

    client = TestClient(api_module.app)
    response = client.post("/ask", json={"q": "anything"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["citations"]) == 1
    assert body["answer"] is None


@requires_db
def test_ask_with_no_evidence_returns_the_explicit_negative(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setattr(api_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())

    client = TestClient(api_module.app)
    response = client.post("/ask", json={"q": "anything"})

    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == []
    assert body["answer"] is None


@requires_db
def test_get_index_job_404s_for_an_unknown_id(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    client = TestClient(api_module.app)
    response = client.get("/index/999999")
    assert response.status_code == 404
