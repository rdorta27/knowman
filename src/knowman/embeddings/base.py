from abc import ABC, abstractmethod


class EmbeddingsProvider(ABC):
    """Turns text into vectors. One implementation per backend: Ollama locally,
    and an in-process model where no Ollama service is available."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order."""
