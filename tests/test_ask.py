from conftest import requires_db

from knowman.ask import ask
from knowman.embeddings.base import EmbeddingsProvider
from knowman.llm.base import LLMProvider
from knowman.retrieval import Citation
from knowman.store import Chunk

_NEAR = [1.0, 0.0, 0.0] + [0.0] * 765
_FAR = [0.0, 1.0, 0.0] + [0.0] * 765


class FixedEmbeddings(EmbeddingsProvider):
    def __init__(self, vector: list[float]) -> None:
        self._vector = vector

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector for _ in texts]


class UnavailableLLM(LLMProvider):
    def is_available(self) -> bool:
        return False

    def generate(self, query: str, citations: list[Citation]) -> str:
        raise AssertionError("should never be called when unavailable")


class FakeLLM(LLMProvider):
    def is_available(self) -> bool:
        return True

    def generate(self, query: str, citations: list[Citation]) -> str:
        return f"answer for {query} using {len(citations)} citation(s)"


@requires_db
def test_ask_with_no_evidence_returns_no_citations_and_no_answer(store):
    result = ask("query", store, FixedEmbeddings(_NEAR), FakeLLM(), k=3, max_distance=0.01)
    assert result.citations == []
    assert result.answer is None


@requires_db
def test_ask_with_evidence_but_no_provider_returns_citations_only(store):
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "text", _NEAR)])
    result = ask("query", store, FixedEmbeddings(_NEAR), None, k=3, max_distance=1.0)
    assert len(result.citations) == 1
    assert result.answer is None


@requires_db
def test_ask_with_evidence_but_unavailable_provider_returns_citations_only(store):
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "text", _NEAR)])
    result = ask("query", store, FixedEmbeddings(_NEAR), UnavailableLLM(), k=3, max_distance=1.0)
    assert len(result.citations) == 1
    assert result.answer is None


@requires_db
def test_ask_with_evidence_and_available_provider_returns_an_answer(store):
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "text", _NEAR)])
    result = ask("query", store, FixedEmbeddings(_NEAR), FakeLLM(), k=3, max_distance=1.0)
    assert result.answer == "answer for query using 1 citation(s)"
