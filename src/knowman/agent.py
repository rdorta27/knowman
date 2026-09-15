from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from knowman.config import get_settings
from knowman.embeddings import get_embeddings_provider
from knowman.formatting import format_citations
from knowman.ingest import ingest_path
from knowman.logging_setup import configure_json_logging, get_logger
from knowman.retrieval import search
from knowman.store import Store

logger = get_logger("knowman.agent")

_SYSTEM_PROMPT = """You are knowman's note-taking assistant. You have two tools:
search_notes and write_note. Always use a tool to accomplish the user's
request — never just describe what you would do in plain text.

- If asked to look something up, remember something, or check what's known
  about a topic: call search_notes.
- If asked to take a note, write down a decision, or record something for
  later: you MUST call the write_note tool. Do not write the note's content
  as your chat reply — that does not save anything. Calling write_note IS
  how you write the note; there is no other way.
- A prior search_notes call finding no evidence is not a reason to stop —
  it means the note doesn't exist yet, so you still need to call write_note
  to create it.
- Your final chat reply (after any tool calls) should be at most one short
  sentence confirming what you did — not a repeat of the note's content.
"""


class UnsafeNotePathError(Exception):
    """Raised when write_note's filename would escape the corpus directory."""


def _resolve_note_path(filename: str, corpus_root: Path) -> Path:
    candidate = (corpus_root / filename).resolve()
    corpus_root = corpus_root.resolve()
    if not candidate.is_relative_to(corpus_root):
        raise UnsafeNotePathError(f"{filename!r} escapes the corpus directory")
    return candidate


@tool
def search_notes(query: str) -> str:
    """Search the note index and return matching citations, or a message
    saying there's no evidence for the query."""
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    k, max_distance = settings.retrieval_default_k, settings.retrieval_max_distance
    citations = search(query, store, embeddings, k, max_distance)
    return format_citations(citations)


@tool
def write_note(filename: str, content: str) -> str:
    """Write a new Markdown note into the local corpus and index it
    immediately. filename is relative to the corpus root (e.g.
    "meeting-2026-09-15.md") and must not escape it."""
    settings = get_settings()
    corpus_root = Path(settings.corpus_path)
    path = _resolve_note_path(filename, corpus_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    ingest_path(path, store, embeddings, root=corpus_root)

    return f"wrote and indexed {filename}"


def run_agent(instruction: str) -> str:
    configure_json_logging()
    settings = get_settings()
    model = ChatOllama(model=settings.agent_model, base_url=settings.ollama_url, reasoning=False)
    graph = create_react_agent(model, tools=[search_notes, write_note], prompt=_SYSTEM_PROMPT)

    result = graph.invoke({"messages": [{"role": "user", "content": instruction}]})

    for message in result["messages"]:
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                logger.info(
                    "agent step",
                    extra={"extra_fields": {"tool": call["name"], "args": call["args"]}},
                )
        elif isinstance(message, ToolMessage):
            logger.info(
                "agent step result",
                extra={"extra_fields": {"tool": message.name, "result": str(message.content)}},
            )

    final = result["messages"][-1]
    return str(final.content)
