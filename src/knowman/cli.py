import argparse
from pathlib import Path

from knowman.config import get_settings
from knowman.embeddings import get_embeddings_provider
from knowman.ingest import ingest_path
from knowman.store import Store

_DEFAULT_CORPUS = Path("corpus/dummy")


def _cmd_db_init(_args: argparse.Namespace) -> None:
    settings = get_settings()
    Store(settings.database_url).init_schema()
    print("schema applied")


def _cmd_ingest(args: argparse.Namespace) -> None:
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    count = ingest_path(Path(args.path), store, embeddings)
    print(f"ingested {count} chunk(s) from {args.path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="knowman")
    subparsers = parser.add_subparsers(required=True)

    db_init = subparsers.add_parser("db-init", help="apply the database schema")
    db_init.set_defaults(func=_cmd_db_init)

    ingest = subparsers.add_parser("ingest", help="ingest Markdown notes into the index")
    ingest.add_argument("--path", default=str(_DEFAULT_CORPUS))
    ingest.set_defaults(func=_cmd_ingest)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
