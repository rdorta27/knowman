from dataclasses import dataclass

from knowman.embeddings.base import EmbeddingsProvider
from knowman.llm.base import LLMProvider
from knowman.retrieval import Citation, search
from knowman.store import Store


@dataclass(frozen=True)
class AskResult:
    citations: list[Citation]
    answer: str | None


def ask(
    query: str,
    store: Store,
    embeddings: EmbeddingsProvider,
    llm_provider: LLMProvider | None,
    k: int,
    max_distance: float,
) -> AskResult:
    """Three states: no evidence -> no citations, no answer (the same
    explicit negative as retrieval); evidence but no usable provider ->
    citations, no answer; evidence and a ready provider -> citations plus
    a generated answer grounded in them."""
    citations = search(query, store, embeddings, k, max_distance)
    if not citations:
        return AskResult(citations=[], answer=None)
    if llm_provider is None or not llm_provider.is_available():
        return AskResult(citations=citations, answer=None)
    answer = llm_provider.generate(query, citations)
    return AskResult(citations=citations, answer=answer)
