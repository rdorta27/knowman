import httpx

from knowman.embeddings.base import EmbeddingsProvider


class OllamaEmbeddingsError(Exception):
    """Raised when Ollama fails to produce an embedding."""


class OllamaEmbeddings(EmbeddingsProvider):
    def __init__(self, url: str, model: str) -> None:
        self._url = url.rstrip("/")
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        with httpx.Client(base_url=self._url, timeout=60.0) as client:
            for text in texts:
                response = client.post(
                    "/api/embeddings", json={"model": self._model, "prompt": text}
                )
                if response.status_code != 200:
                    raise OllamaEmbeddingsError(
                        f"ollama returned {response.status_code}: {response.text}"
                    )
                body = response.json()
                embedding = body.get("embedding")
                if not embedding:
                    raise OllamaEmbeddingsError(f"ollama response missing embedding: {body}")
                vectors.append(embedding)
        return vectors
