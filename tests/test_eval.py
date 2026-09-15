from conftest import requires_db

from knowman.embeddings.base import EmbeddingsProvider
from knowman.eval import EvalQuestion, run_eval
from knowman.llm.base import LLMProvider
from knowman.retrieval import Citation
from knowman.store import Chunk

_NEAR = [1.0, 0.0, 0.0] + [0.0] * 765
_FAR = [0.0, 1.0, 0.0] + [0.0] * 765


class KeyedEmbeddings(EmbeddingsProvider):
    """Returns _NEAR for questions containing 'near', _FAR otherwise —
    lets a dataset mix questions that should and shouldn't match."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_NEAR if "near" in t else _FAR for t in texts]


class FakeLLM(LLMProvider):
    def is_available(self) -> bool:
        return True

    def generate(self, query: str, citations: list[Citation]) -> str:
        return "an answer"


@requires_db
def test_run_eval_scores_a_fully_passing_dataset_as_1(store):
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "text", _NEAR)])
    dataset = [
        EvalQuestion("q1", "a near question", "citation", "a.md"),
        EvalQuestion("q2", "a far question", "negative", None),
    ]
    result = run_eval(dataset, store, KeyedEmbeddings(), None, k=3, max_distance=0.01)
    assert result.groundedness == 1.0
    assert result.correct == 2
    assert result.total == 2


@requires_db
def test_run_eval_scores_a_mixed_dataset_partially(store):
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "text", _NEAR)])
    dataset = [
        EvalQuestion("q1", "a near question", "citation", "wrong-path.md"),
        EvalQuestion("q2", "a far question", "negative", None),
    ]
    result = run_eval(dataset, store, KeyedEmbeddings(), None, k=3, max_distance=0.01)
    assert result.groundedness == 0.5
    assert [r.correct for r in result.results] == [False, True]


@requires_db
def test_run_eval_without_a_provider_has_no_answered_count(store):
    dataset = [EvalQuestion("q1", "a far question", "negative", None)]
    result = run_eval(dataset, store, KeyedEmbeddings(), None, k=3, max_distance=0.01)
    assert result.answered_count is None


@requires_db
def test_run_eval_with_a_provider_counts_answered_citation_questions(store):
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "text", _NEAR)])
    dataset = [EvalQuestion("q1", "a near question", "citation", "a.md")]
    result = run_eval(dataset, store, KeyedEmbeddings(), FakeLLM(), k=3, max_distance=1.0)
    assert result.answered_count == 1


@requires_db
def test_run_eval_reports_delta_against_the_previous_run(store):
    dataset = [EvalQuestion("q1", "a far question", "negative", None)]
    first = run_eval(dataset, store, KeyedEmbeddings(), None, k=3, max_distance=0.01)
    assert first.delta is None

    second = run_eval(dataset, store, KeyedEmbeddings(), None, k=3, max_distance=0.01)
    assert second.delta == 0.0
