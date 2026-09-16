from conftest import _TEST_DATABASE_URL, requires_db
from fastapi.testclient import TestClient

import knowman.api as api_module
from knowman.embeddings.base import EmbeddingsProvider
from knowman.eval import EvalQuestion
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
def test_get_eval_returns_groundedness_and_no_delta_on_first_run(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setattr(api_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())
    monkeypatch.setattr(
        api_module, "load_dataset", lambda: [EvalQuestion("q1", "anything", "negative", None)]
    )

    client = TestClient(api_module.app)
    response = client.get("/eval")

    assert response.status_code == 200
    body = response.json()
    assert body["groundedness"] == 1.0
    assert body["delta"] is None


@requires_db
def test_get_eval_history_lists_recorded_runs(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    store.record_eval_run(0.9, 10, 9, None, [])

    client = TestClient(api_module.app)
    response = client.get("/eval/history")

    assert response.status_code == 200
    runs = response.json()["runs"]
    assert len(runs) == 1
    assert runs[0]["groundedness"] == 0.9


@requires_db
def test_get_index_job_404s_for_an_unknown_id(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    client = TestClient(api_module.app)
    response = client.get("/index/999999")
    assert response.status_code == 404


@requires_db
def test_status_reports_disk_index_and_queue_counts(store, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setenv("CORPUS_PATH", str(tmp_path))
    (tmp_path / "a.md").write_text("x")
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "text", _NEAR)])

    client = TestClient(api_module.app)
    response = client.get("/status")

    assert response.status_code == 200
    body = response.json()
    assert body["files_on_disk"] == 1
    assert body["files_indexed"] == 1
    assert body["chunks"] == 1


@requires_db
def test_files_lists_indexed_and_unindexed_entries(store, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setenv("CORPUS_PATH", str(tmp_path))
    (tmp_path / "a.md").write_text("x")
    (tmp_path / "b.md").write_text("y")
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "text", _NEAR)])

    client = TestClient(api_module.app)
    response = client.get("/files")

    assert response.status_code == 200
    by_path = {f["path"]: f for f in response.json()}
    assert by_path["a.md"]["indexed"] is True
    assert by_path["b.md"]["indexed"] is False


@requires_db
def test_jobs_recent_lists_newest_first(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    first = store.enqueue_job("ingest_path", {"path": "a"})
    second = store.enqueue_job("ingest_path", {"path": "b"})

    client = TestClient(api_module.app)
    response = client.get("/jobs/recent")

    assert response.status_code == 200
    ids = [job["id"] for job in response.json()]
    assert ids[:2] == [second, first]


@requires_db
def test_traces_recent_lists_newest_first(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    store.record_trace(
        prompt_id=None,
        query="q1",
        citation_count=0,
        has_citation=False,
        latency_ms=1.0,
        tokens_approx=1,
        answered=False,
    )
    store.record_trace(
        prompt_id=None,
        query="q2",
        citation_count=0,
        has_citation=False,
        latency_ms=1.0,
        tokens_approx=1,
        answered=False,
    )

    client = TestClient(api_module.app)
    response = client.get("/traces/recent")

    assert response.status_code == 200
    queries = [t["query"] for t in response.json()]
    assert queries[:2] == ["q2", "q1"]


def test_dashboard_serves_the_static_page_with_no_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret")
    client = TestClient(api_module.app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@requires_db
def test_status_requires_the_token_like_any_other_route(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "secret")
    client = TestClient(api_module.app)

    response = client.get("/status")

    assert response.status_code == 401
