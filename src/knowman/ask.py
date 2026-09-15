import time
from dataclasses import dataclass

from knowman.embeddings.base import EmbeddingsProvider
from knowman.llm.base import LLMProvider, current_prompt_version
from knowman.retrieval import Citation, search
from knowman.store import Store


@dataclass(frozen=True)
class AskResult:
    citations: list[Citation]
    answer: str | None


def _approx_tokens(*texts: str) -> int:
    """Rough token estimate (~4 chars/token) — good enough for an
    observability figure, not an accounting one; no tokenizer dependency."""
    return sum(len(t) for t in texts) // 4


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
    a generated answer grounded in them. Every call is traced: prompt_id
    is only set when an answer was actually generated."""
    started = time.perf_counter()
    citations = search(query, store, embeddings, k, max_distance)
    answer: str | None = None
    prompt_id: str | None = None

    if citations and llm_provider is not None and llm_provider.is_available():
        answer = llm_provider.generate(query, citations)
        prompt_id = current_prompt_version()

    latency_ms = (time.perf_counter() - started) * 1000
    tokens_approx = _approx_tokens(query, *(c.text for c in citations), answer or "")
    store.record_trace(
        prompt_id=prompt_id,
        query=query,
        citation_count=len(citations),
        has_citation=bool(citations),
        latency_ms=latency_ms,
        tokens_approx=tokens_approx,
        answered=answer is not None,
    )

    return AskResult(citations=citations, answer=answer)
