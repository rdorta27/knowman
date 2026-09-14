from knowman.chunking import chunk_markdown, content_hash


def test_chunk_markdown_splits_on_blank_lines():
    text = "# Title\n\nFirst paragraph.\n\nSecond paragraph.\n"
    chunks = chunk_markdown(text)
    assert [c.text for c in chunks] == ["# Title", "First paragraph.", "Second paragraph."]


def test_chunk_markdown_line_ranges_are_1_indexed_and_inclusive():
    text = "line one\nline two\n\nline four\n"
    chunks = chunk_markdown(text)
    assert (chunks[0].line_start, chunks[0].line_end) == (1, 2)
    assert (chunks[1].line_start, chunks[1].line_end) == (4, 4)


def test_chunk_markdown_keeps_a_multiline_block_as_one_chunk():
    text = "line one\nline two\nline three\n"
    chunks = chunk_markdown(text)
    assert len(chunks) == 1
    assert chunks[0].text == "line one\nline two\nline three"


def test_content_hash_is_stable_and_sensitive_to_change():
    assert content_hash("same") == content_hash("same")
    assert content_hash("same") != content_hash("different")
