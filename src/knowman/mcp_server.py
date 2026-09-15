from mcp.server.mcpserver import MCPServer

from knowman.ask import ask as run_ask
from knowman.config import get_settings
from knowman.embeddings import get_embeddings_provider
from knowman.llm import get_llm_provider
from knowman.retrieval import Citation
from knowman.retrieval import search as run_search
from knowman.store import Store

mcp = MCPServer(name="knowman")


def _citation_dict(citation: Citation) -> dict:
    return {
        "path": citation.path,
        "line_start": citation.line_start,
        "line_end": citation.line_end,
        "text": citation.text,
        "distance": citation.distance,
    }


@mcp.tool()
def search(query: str, k: int | None = None) -> dict:
    """Search the note index and return citations (path + line range +
    text), or an empty list when there's no evidence for the query."""
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    resolved_k = k if k is not None else settings.retrieval_default_k
    citations = run_search(query, store, embeddings, resolved_k, settings.retrieval_max_distance)
    return {"citations": [_citation_dict(c) for c in citations]}


@mcp.tool()
def ask(query: str, k: int | None = None) -> dict:
    """Ask a question. Always returns citations; also returns a generated
    answer when an LLM provider is configured and there's evidence."""
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    llm_provider = get_llm_provider(settings)
    resolved_k = k if k is not None else settings.retrieval_default_k
    result = run_ask(
        query, store, embeddings, llm_provider, resolved_k, settings.retrieval_max_distance
    )
    return {
        "citations": [_citation_dict(c) for c in result.citations],
        "answer": result.answer,
    }


def run() -> None:
    mcp.run()
