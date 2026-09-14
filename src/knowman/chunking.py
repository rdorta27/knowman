import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    line_start: int
    line_end: int
    text: str


def chunk_markdown(content: str) -> list[TextChunk]:
    """Split Markdown into line-addressable chunks: one chunk per block of
    consecutive non-blank lines. Keeps each citation pointing at a single
    idea instead of a whole file."""
    lines = content.splitlines()
    chunks: list[TextChunk] = []
    start: int | None = None

    for i, line in enumerate(lines, start=1):
        if line.strip():
            if start is None:
                start = i
        elif start is not None:
            chunks.append(TextChunk(start, i - 1, "\n".join(lines[start - 1 : i - 1])))
            start = None

    if start is not None:
        chunks.append(TextChunk(start, len(lines), "\n".join(lines[start - 1 :])))

    return chunks


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
