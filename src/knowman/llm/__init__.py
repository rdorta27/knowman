from knowman.config import Settings
from knowman.llm.base import LLMProvider
from knowman.llm.claude import ClaudeProvider
from knowman.llm.grok import GrokProvider
from knowman.llm.ollama import OllamaChat
from knowman.llm.openai import OpenAIProvider

__all__ = ["LLMProvider", "get_llm_provider"]

_PROVIDERS = {
    "ollama": lambda s: OllamaChat(url=s.ollama_url, model=s.chat_model),
    "claude": lambda s: ClaudeProvider(api_key=s.anthropic_api_key, model=s.anthropic_model),
    "openai": lambda s: OpenAIProvider(api_key=s.openai_api_key, model=s.openai_model),
    "grok": lambda s: GrokProvider(api_key=s.xai_api_key, model=s.xai_model),
}


def get_llm_provider(settings: Settings) -> LLMProvider | None:
    """None when no provider is configured — ask() then falls back to
    retrieval-only, per "sin clave, solo retrieval"."""
    if not settings.llm_provider:
        return None
    factory = _PROVIDERS.get(settings.llm_provider)
    if factory is None:
        raise ValueError(f"unknown llm provider: {settings.llm_provider!r}")
    return factory(settings)
