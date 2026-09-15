import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    line_start: int
    line_end: int
    text: str


def _split_into_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Group consecutive non-blank lines into (start, end) line ranges, 1-indexed."""
    blocks: list[tuple[int, int]] = []
    start: int | None = None
    for i, line in enumerate(lines, start=1):
        if line.strip():
            if start is None:
                start = i
        elif start is not None:
            blocks.append((start, i - 1))
            start = None
    if start is not None:
        blocks.append((start, len(lines)))
    return blocks


def _is_heading_only(lines: list[str], block: tuple[int, int]) -> bool:
    start, end = block
    return start == end and lines[start - 1].lstrip().startswith("#")


def chunk_markdown(content: str) -> list[TextChunk]:
    """Split Markdown into line-addressable chunks: one chunk per block of
    consecutive non-blank lines, except a lone heading line, which merges
    into the next block instead of standing alone — a title with no body
    text embeds too weakly/generically to be a useful citation target."""
    lines = content.splitlines()
    blocks = _split_into_blocks(lines)

    merged: list[tuple[int, int]] = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if _is_heading_only(lines, block) and i + 1 < len(blocks):
            merged.append((block[0], blocks[i + 1][1]))
            i += 2
        else:
            merged.append(block)
            i += 1

    return [TextChunk(start, end, "\n".join(lines[start - 1 : end])) for start, end in merged]


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
