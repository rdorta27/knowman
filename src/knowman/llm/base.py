from abc import ABC, abstractmethod
from importlib.resources import files

from knowman.config import get_settings
from knowman.retrieval import Citation

_PROMPTS_DIR = files("knowman") / "prompts"


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


def current_prompt_version() -> str:
    return get_settings().prompt_version


def build_prompt(query: str, citations: list[Citation], version: str | None = None) -> str:
    """Loads knowman/prompts/{version}.txt — the prompt's wording lives outside the
    code, so changing it is a new file plus a settings change, not a
    Python edit. version defaults to the configured prompt_version."""
    version = version or current_prompt_version()
    template = (_PROMPTS_DIR / f"{version}.txt").read_text()
    context = "\n\n".join(f"[{c.path}:L{c.line_start}-L{c.line_end}]\n{c.text}" for c in citations)
    return template.format(query=query, context=context)
