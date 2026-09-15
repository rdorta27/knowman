from abc import ABC, abstractmethod

from knowman.retrieval import Citation


class LLMProvider(ABC):
    """Generates an answer grounded in retrieved citations. One implementation
    per backend (Ollama locally, Claude/OpenAI/Grok with a key)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider is ready to call — false when a required
        API key isn't configured. `ask` falls back to retrieval-only when
        no configured provider is available."""

    @abstractmethod
    def generate(self, query: str, citations: list[Citation]) -> str:
        """Answer query using only the given citations as context."""


_PROMPT_TEMPLATE = """Answer the question using only the excerpts below. \
If they don't contain the answer, say so plainly instead of guessing.

Question: {query}

Excerpts:
{context}
"""


def build_prompt(query: str, citations: list[Citation]) -> str:
    context = "\n\n".join(f"[{c.path}:L{c.line_start}-L{c.line_end}]\n{c.text}" for c in citations)
    return _PROMPT_TEMPLATE.format(query=query, context=context)
