from abc import ABC, abstractmethod


class EmbeddingsProvider(ABC):
    """Turns text into vectors. One implementation per backend (Ollama locally, an
    in-process model on Azure — see ki/project/vision/VISION.md § Stack)."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order."""
