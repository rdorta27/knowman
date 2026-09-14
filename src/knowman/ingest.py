from pathlib import Path

from knowman.chunking import chunk_markdown, content_hash
from knowman.embeddings.base import EmbeddingsProvider
from knowman.store import Chunk, Store


def ingest_path(path: Path, store: Store, embeddings: EmbeddingsProvider) -> int:
    """Parse every .md file under path, embed its chunks, and persist them.
    Re-running over the same corpus does not duplicate rows: each file's
    prior chunks are replaced wholesale (see Store.upsert_chunks)."""
    total = 0
    for md_file in sorted(path.rglob("*.md")):
        relative_path = str(md_file.relative_to(path))
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
