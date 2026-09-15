from conftest import _TEST_DATABASE_URL, requires_db

import knowman.mcp_server as mcp_module
from knowman.embeddings.base import EmbeddingsProvider
from knowman.store import Chunk

_NEAR = [1.0, 0.0, 0.0] + [0.0] * 765


class FixedEmbeddings(EmbeddingsProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_NEAR for _ in texts]


@requires_db
def test_search_tool_returns_citations_for_a_matching_query(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setattr(mcp_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "matching text", _NEAR)])

    result = mcp_module.search("anything")

    assert len(result["citations"]) == 1
    assert result["citations"][0]["path"] == "a.md"


@requires_db
def test_search_tool_returns_empty_citations_for_an_out_of_corpus_query(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    far = [0.0, 1.0, 0.0] + [0.0] * 765
    monkeypatch.setattr(mcp_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "unrelated", far)])

    result = mcp_module.search("anything")

    assert result["citations"] == []


@requires_db
def test_ask_tool_returns_null_answer_with_no_provider(store, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setattr(mcp_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())
    monkeypatch.setattr(mcp_module, "get_llm_provider", lambda settings: None)
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "matching text", _NEAR)])

    result = mcp_module.ask("anything")

    assert len(result["citations"]) == 1
    assert result["answer"] is None
