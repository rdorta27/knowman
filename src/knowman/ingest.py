from pathlib import Path

from knowman.chunking import chunk_markdown, content_hash
from knowman.embeddings.base import EmbeddingsProvider
from knowman.store import Chunk, Store


def ingest_path(
    path: Path, store: Store, embeddings: EmbeddingsProvider, root: Path | None = None
) -> int:
    """Embed and persist path: every .md file under it if it's a directory,
    or just that one file. Citations are stored relative to root (path
    itself, for a directory; its parent, for a single file), so a watcher
    ingesting one changed file cites it the same way a full directory
    ingest would. Re-running does not duplicate rows: each file's prior
    chunks are replaced wholesale (see Store.upsert_chunks)."""
    if path.is_dir():
        root = root or path
        md_files = sorted(path.rglob("*.md"))
    else:
        root = root or path.parent
        md_files = [path]

    total = 0
    for md_file in md_files:
        relative_path = str(md_file.relative_to(root))
        text_chunks = chunk_markdown(md_file.read_text())
        if not text_chunks:
            continue
        vectors = embeddings.embed([chunk.text for chunk in text_chunks])
        chunks = [
            Chunk(
                path=relative_path,
                content_hash=content_hash(text_chunk.text),
                line_start=text_chunk.line_start,
                line_end=text_chunk.line_end,
                text=text_chunk.text,
                embedding=vector,
            )
            for text_chunk, vector in zip(text_chunks, vectors, strict=True)
        ]
        total += store.upsert_chunks(chunks)
    return total
