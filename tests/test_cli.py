from pathlib import Path

import psycopg
import pytest
from conftest import _TEST_DATABASE_URL, requires_db

import knowman.cli as cli_module
from knowman.embeddings.base import EmbeddingsProvider
from knowman.eval import EvalQuestion
from knowman.llm.base import LLMProvider
from knowman.retrieval import Citation
from knowman.store import Chunk

_NEAR = [1.0, 0.0, 0.0] + [0.0] * 765
_FAR = [0.0, 1.0, 0.0] + [0.0] * 765


class FixedEmbeddings(EmbeddingsProvider):
    def __init__(self, vector: list[float] | None = None) -> None:
        self._vector = vector or _NEAR

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector for _ in texts]


class FakeLLM(LLMProvider):
    def is_available(self) -> bool:
        return True

    def generate(self, query: str, citations: list[Citation]) -> str:
        return "a generated answer"


def _run(argv: list[str]) -> None:
    """Drive a subcommand the way main() does, without touching sys.argv."""
    args = cli_module.build_parser().parse_args(argv)
    args.func(args)


@pytest.fixture
def local_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_DATABASE_URL)
    monkeypatch.setattr(cli_module, "get_embeddings_provider", lambda settings: FixedEmbeddings())


@requires_db
def test_db_init_applies_the_schema_at_the_detected_dimension(local_db, capsys):
    with psycopg.connect(_TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS chunks")

    _run(["db-init"])

    assert "768" in capsys.readouterr().out
    with psycopg.connect(_TEST_DATABASE_URL) as conn:
        row = conn.execute("""
            SELECT atttypmod FROM pg_attribute
            WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'
            """).fetchone()
    assert row[0] == 768


@requires_db
def test_ingest_reads_the_path_it_is_given(store, local_db, tmp_path: Path, capsys):
    (tmp_path / "note.md").write_text("some content\n")

    _run(["ingest", "--path", str(tmp_path)])

    assert "ingested 1 chunk(s)" in capsys.readouterr().out
    assert store.count_chunks() == 1


@requires_db
def test_ingest_falls_back_to_the_configured_corpus_path(
    store, local_db, tmp_path: Path, monkeypatch, capsys
):
    (tmp_path / "note.md").write_text("some content\n")
    monkeypatch.setenv("CORPUS_PATH", str(tmp_path))

    _run(["ingest"])

    assert str(tmp_path) in capsys.readouterr().out
    assert store.count_chunks() == 1


@requires_db
def test_search_prints_the_citations(store, local_db, capsys):
    store.upsert_chunks([Chunk("a.md", "h1", 3, 5, "matching text", _NEAR)])

    _run(["search", "anything"])

    assert "a.md:L3-L5" in capsys.readouterr().out


@requires_db
def test_ask_prints_the_explicit_negative_without_evidence(store, local_db, capsys):
    _run(["ask", "anything"])

    assert capsys.readouterr().out.strip() == "No evidence found for that query."


@requires_db
def test_ask_prints_only_citations_without_a_provider(store, local_db, monkeypatch, capsys):
    monkeypatch.setattr(cli_module, "get_llm_provider", lambda settings: None)
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "matching text", _NEAR)])

    _run(["ask", "anything"])

    output = capsys.readouterr().out
    assert "a.md:L1-L1" in output
    assert "Fuentes:" not in output


@requires_db
def test_ask_prints_the_answer_and_its_sources_with_a_provider(
    store, local_db, monkeypatch, capsys
):
    monkeypatch.setattr(cli_module, "get_llm_provider", lambda settings: FakeLLM())
    store.upsert_chunks([Chunk("a.md", "h1", 1, 1, "matching text", _NEAR)])

    _run(["ask", "anything"])

    output = capsys.readouterr().out
    assert "a generated answer" in output
    assert "Fuentes:" in output
    assert "a.md:L1-L1" in output


@requires_db
def test_eval_prints_groundedness_and_its_failing_questions(store, local_db, monkeypatch, capsys):
    monkeypatch.setattr(cli_module, "get_llm_provider", lambda settings: None)
    monkeypatch.setattr(
        cli_module,
        "load_dataset",
        lambda: [
            EvalQuestion("q1", "a question", "negative", None),
            EvalQuestion("q2", "another question", "citation", "missing.md"),
        ],
    )

    _run(["eval"])

    output = capsys.readouterr().out
    assert "groundedness: 50.00% (1/2)" in output
    assert "delta: n/a (first run)" in output
    assert "q2 (citation)" in output


def test_write_hands_the_instruction_to_the_agent(monkeypatch, capsys):
    import knowman.agent as agent_module

    monkeypatch.setattr(agent_module, "run_agent", lambda instruction: f"did: {instruction}")

    _run(["write", "take a note"])

    assert "did: take a note" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["worker"], "_cmd_worker"),
        (["watch"], "_cmd_watch"),
        (["mcp"], "_cmd_mcp"),
    ],
)
def test_parser_wires_each_long_running_command(argv: list[str], expected: str):
    """These block forever once called, so the wiring is what gets asserted."""
    args = cli_module.build_parser().parse_args(argv)
    assert args.func.__name__ == expected
