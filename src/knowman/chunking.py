import hashlib
from dataclasses import dataclass

# A safety ceiling, not a knob: a block this long already stopped being a
# single citable thought, and left uncapped it becomes one oversized
# embedding call and a citation that dumps the whole block back verbatim
# (measured: an unbroken 50,000-line block produced one 3.5MB chunk).
_MAX_CHUNK_LINES = 200


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


def _split_oversized(block: tuple[int, int]) -> list[tuple[int, int]]:
    """A block at or under the cap is returned unchanged; a longer one splits
    into consecutive sub-ranges of at most _MAX_CHUNK_LINES lines each, so no
    single chunk's embedding call or citation payload is unbounded."""
    start, end = block
    if end - start + 1 <= _MAX_CHUNK_LINES:
        return [block]
    sub_blocks = []
    sub_start = start
    while sub_start <= end:
        sub_end = min(sub_start + _MAX_CHUNK_LINES - 1, end)
        sub_blocks.append((sub_start, sub_end))
        sub_start = sub_end + 1
    return sub_blocks


def chunk_markdown(content: str) -> list[TextChunk]:
    """Split Markdown into line-addressable chunks: one chunk per block of
    consecutive non-blank lines, except a lone heading line, which merges
    into the next block instead of standing alone — a title with no body
    text embeds too weakly/generically to be a useful citation target. A
    block longer than _MAX_CHUNK_LINES is further split into consecutive
    sub-chunks, each still keeping its own exact line range."""
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

    capped = [sub for block in merged for sub in _split_oversized(block)]

    return [TextChunk(start, end, "\n".join(lines[start - 1 : end])) for start, end in capped]


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
