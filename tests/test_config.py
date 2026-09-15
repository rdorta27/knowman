import pytest

from knowman.config import Settings
from knowman.embeddings import get_embeddings_provider
from knowman.embeddings.ollama import OllamaEmbeddings
from knowman.llm import get_llm_provider
from knowman.llm.claude import ClaudeProvider
from knowman.llm.grok import GrokProvider
from knowman.llm.ollama import OllamaChat
from knowman.llm.openai import OpenAIProvider


def _settings(**overrides) -> Settings:
    """Ignore the developer's .env: Settings reads it from the working
    directory, and install.sh writes one into every checkout, so a
    defaults test would assert whatever that file happens to say."""
    return Settings(_env_file=None, **overrides)


def test_settings_fall_back_to_their_declared_defaults():
    settings = _settings()
    assert settings.embeddings_provider == "ollama"
    assert settings.embeddings_model == "qwen3-embedding:0.6b"
    assert settings.corpus_path == "corpus/dummy"
    assert settings.retrieval_default_k == 3
    assert settings.retrieval_max_distance == 0.5
    assert settings.prompt_version == "ask_v1"
    assert settings.llm_provider is None


def test_settings_read_a_value_from_the_environment(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_MODEL", "some-other-model")
    monkeypatch.setenv("RETRIEVAL_DEFAULT_K", "7")
    settings = _settings()
    assert settings.embeddings_model == "some-other-model"
    assert settings.retrieval_default_k == 7


def test_get_embeddings_provider_returns_the_ollama_provider():
    assert isinstance(get_embeddings_provider(_settings()), OllamaEmbeddings)


def test_get_embeddings_provider_rejects_an_unknown_provider():
    with pytest.raises(ValueError, match="unknown embeddings provider"):
        get_embeddings_provider(_settings(embeddings_provider="pinecone"))


def test_get_llm_provider_is_none_when_none_is_configured():
    assert get_llm_provider(_settings()) is None


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("ollama", OllamaChat),
        ("claude", ClaudeProvider),
        ("openai", OpenAIProvider),
        ("grok", GrokProvider),
    ],
)
def test_get_llm_provider_builds_the_named_provider(name: str, expected: type):
    assert isinstance(get_llm_provider(_settings(llm_provider=name)), expected)


def test_get_llm_provider_rejects_an_unknown_provider():
    with pytest.raises(ValueError, match="unknown llm provider"):
        get_llm_provider(_settings(llm_provider="bedrock"))
