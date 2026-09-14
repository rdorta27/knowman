from dataclasses import dataclass

from knowman.embeddings.base import EmbeddingsProvider
from knowman.store import Store


@dataclass(frozen=True)
class Citation:
    path: str
    line_start: int
    line_end: int
    text: str
    distance: float


def search(
    query: str,
    store: Store,
    embeddings: EmbeddingsProvider,
    k: int,
    max_distance: float,
) -> list[Citation]:
    """Return up to k citations for query, dropping anything past
    max_distance. An empty list is the explicit "no evidence" case —
    it's on the caller (CLI, HTTP) to present that as a negative."""
    (query_embedding,) = embeddings.embed([query])
    rows = store.search(query_embedding, k=k)
    return [
        Citation(
            path=row["path"],
            line_start=row["line_start"],
            line_end=row["line_end"],
            text=row["text"],
            distance=row["distance"],
        )
        for row in rows
        if row["distance"] <= max_distance
    ]
