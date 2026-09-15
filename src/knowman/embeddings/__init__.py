from knowman.config import Settings
from knowman.embeddings.base import EmbeddingsProvider
from knowman.embeddings.ollama import OllamaEmbeddings

__all__ = ["EmbeddingsProvider", "detect_dimension", "get_embeddings_provider"]


def get_embeddings_provider(settings: Settings) -> EmbeddingsProvider:
    if settings.embeddings_provider == "ollama":
        return OllamaEmbeddings(url=settings.ollama_url, model=settings.embeddings_model)
    raise ValueError(f"unknown embeddings provider: {settings.embeddings_provider!r}")


def detect_dimension(embeddings: EmbeddingsProvider) -> int:
    (vector,) = embeddings.embed(["dimension probe"])
    return len(vector)
