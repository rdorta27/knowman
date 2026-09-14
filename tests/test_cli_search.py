from knowman.cli import format_citations
from knowman.retrieval import Citation


def test_format_citations_prints_path_and_line_range():
    citations = [Citation("a.md", 3, 5, "some fragment", 0.1)]
    output = format_citations(citations)
    assert "a.md:L3-L5" in output
    assert "some fragment" in output


def test_format_citations_reports_no_evidence_for_an_empty_result():
    assert format_citations([]) == "No evidence found for that query."
