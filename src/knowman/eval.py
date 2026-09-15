import json
from dataclasses import dataclass
from pathlib import Path

from knowman.ask import ask
from knowman.embeddings.base import EmbeddingsProvider
from knowman.llm.base import LLMProvider
from knowman.retrieval import search
from knowman.store import Store

_DEFAULT_DATASET_PATH = Path(__file__).resolve().parents[2] / "eval" / "dataset.json"


@dataclass(frozen=True)
class EvalQuestion:
    id: str
    question: str
    expect: str  # "citation" or "negative"
    expect_path_contains: str | None


@dataclass(frozen=True)
class QuestionResult:
    id: str
    question: str
    expect: str
    correct: bool


@dataclass(frozen=True)
class EvalResult:
    groundedness: float
    total: int
    correct: int
    answered_count: int | None
    results: list[QuestionResult]
    delta: float | None


def load_dataset(path: Path = _DEFAULT_DATASET_PATH) -> list[EvalQuestion]:
    raw = json.loads(path.read_text())
    return [EvalQuestion(**entry) for entry in raw]


def _question_passes(question: EvalQuestion, citations: list) -> bool:
    if question.expect == "negative":
        return not citations
    return any(question.expect_path_contains in c.path for c in citations)


def run_eval(
    dataset: list[EvalQuestion],
    store: Store,
    embeddings: EmbeddingsProvider,
    llm_provider: LLMProvider | None,
    k: int,
    max_distance: float,
) -> EvalResult:
    """Groundedness is a deterministic match rate against the labeled
    dataset — never an LLM judge, so it stays computable with no provider
    configured. When a provider is available, answered_count tracks how
    many citation-expecting questions got a generated answer; that count
    is metadata, not part of the score."""
    results: list[QuestionResult] = []
    answered = 0 if llm_provider is not None and llm_provider.is_available() else None

    for question in dataset:
        citations = search(question.question, store, embeddings, k, max_distance)
        correct = _question_passes(question, citations)
        results.append(
            QuestionResult(
                id=question.id, question=question.question, expect=question.expect, correct=correct
            )
        )
        if answered is not None and question.expect == "citation":
            ask_result = ask(question.question, store, embeddings, llm_provider, k, max_distance)
            if ask_result.answer is not None:
                answered += 1

    total = len(dataset)
    correct = sum(1 for r in results if r.correct)
    groundedness = correct / total if total else 0.0

    previous = store.get_last_eval_run()
    delta = groundedness - previous.groundedness if previous else None

    store.record_eval_run(groundedness, total, correct, answered, [r.__dict__ for r in results])

    return EvalResult(
        groundedness=groundedness,
        total=total,
        correct=correct,
        answered_count=answered,
        results=results,
        delta=delta,
    )
