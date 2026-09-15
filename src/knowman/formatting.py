from knowman.retrieval import Citation


def format_citations(citations: list[Citation]) -> str:
    if not citations:
        return "No evidence found for that query."
    lines = []
    for citation in citations:
        lines.append(f"{citation.path}:L{citation.line_start}-L{citation.line_end}")
        lines.append(f"  {citation.text}")
    return "\n".join(lines)
