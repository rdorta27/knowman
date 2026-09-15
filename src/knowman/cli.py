import argparse
from pathlib import Path

from knowman.ask import ask
from knowman.config import get_settings
from knowman.embeddings import detect_dimension, get_embeddings_provider
from knowman.eval import load_dataset, run_eval
from knowman.ingest import ingest_path
from knowman.llm import get_llm_provider
from knowman.retrieval import Citation, search
from knowman.store import Store
from knowman.watcher import run_watcher
from knowman.worker import run_worker


def format_citations(citations: list[Citation]) -> str:
    if not citations:
        return "No evidence found for that query."
    lines = []
    for citation in citations:
        lines.append(f"{citation.path}:L{citation.line_start}-L{citation.line_end}")
        lines.append(f"  {citation.text}")
    return "\n".join(lines)


def _cmd_db_init(_args: argparse.Namespace) -> None:
    settings = get_settings()
    embeddings = get_embeddings_provider(settings)
    dimension = detect_dimension(embeddings)
    Store(settings.database_url).init_schema(dimension)
    print(f"schema applied (embedding dimension: {dimension})")


def _cmd_ingest(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    path = args.path or settings.corpus_path
    count = ingest_path(Path(path), store, embeddings)
    print(f"ingested {count} chunk(s) from {path}")


def _cmd_worker(_args: argparse.Namespace) -> None:
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    print("worker started, polling for jobs")
    run_worker(store, embeddings)


def _cmd_watch(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = Store(settings.database_url)
    path = Path(args.path or settings.corpus_path)
    print(f"watching {path} for changes")
    run_watcher(path, store)


def _cmd_search(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    k = args.k if args.k is not None else settings.retrieval_default_k
    citations = search(args.query, store, embeddings, k, settings.retrieval_max_distance)
    print(format_citations(citations))


def _cmd_ask(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    llm_provider = get_llm_provider(settings)
    k = args.k if args.k is not None else settings.retrieval_default_k
    result = ask(args.query, store, embeddings, llm_provider, k, settings.retrieval_max_distance)
    if not result.citations:
        print("No evidence found for that query.")
        return
    if result.answer is None:
        print(format_citations(result.citations))
        return
    print(result.answer)
    print("\nFuentes:")
    print(format_citations(result.citations))


def _cmd_eval(_args: argparse.Namespace) -> None:
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    llm_provider = get_llm_provider(settings)
    dataset = load_dataset()
    k, max_distance = settings.retrieval_default_k, settings.retrieval_max_distance
    result = run_eval(dataset, store, embeddings, llm_provider, k, max_distance)
    delta_str = f"{result.delta:+.2%}" if result.delta is not None else "n/a (first run)"
    score = f"{result.groundedness:.2%} ({result.correct}/{result.total})"
    print(f"groundedness: {score}, delta: {delta_str}")
    if result.answered_count is not None:
        print(f"answered: {result.answered_count} citation question(s) got a generated answer")
    failing = [r for r in result.results if not r.correct]
    if failing:
        print("failing questions:")
        for r in failing:
            print(f"  {r.id} ({r.expect}): {r.question}")


def _cmd_mcp(_args: argparse.Namespace) -> None:
    from knowman.mcp_server import run

    run()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="knowman")
    subparsers = parser.add_subparsers(required=True)

    db_init = subparsers.add_parser("db-init", help="apply the database schema")
    db_init.set_defaults(func=_cmd_db_init)

    ingest = subparsers.add_parser("ingest", help="ingest Markdown notes into the index")
    ingest.add_argument("--path", default=None)
    ingest.set_defaults(func=_cmd_ingest)

    worker = subparsers.add_parser("worker", help="poll the jobs table and run pending jobs")
    worker.set_defaults(func=_cmd_worker)

    watch = subparsers.add_parser("watch", help="watch a directory and enqueue jobs on change")
    watch.add_argument("--path", default=None)
    watch.set_defaults(func=_cmd_watch)

    search_cmd = subparsers.add_parser("search", help="search the index and print citations")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--k", type=int, default=None)
    search_cmd.set_defaults(func=_cmd_search)

    ask_cmd = subparsers.add_parser("ask", help="ask a question, with citations")
    ask_cmd.add_argument("query")
    ask_cmd.add_argument("--k", type=int, default=None)
    ask_cmd.set_defaults(func=_cmd_ask)

    eval_cmd = subparsers.add_parser("eval", help="run the eval dataset and report groundedness")
    eval_cmd.set_defaults(func=_cmd_eval)

    mcp_cmd = subparsers.add_parser("mcp", help="run the MCP server over stdio")
    mcp_cmd.set_defaults(func=_cmd_mcp)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
