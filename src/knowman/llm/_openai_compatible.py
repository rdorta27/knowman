import httpx

from knowman.llm.base import LLMProvider, build_prompt
from knowman.retrieval import Citation


class OpenAICompatibleProvider(LLMProvider):
    """Shared implementation for chat-completions APIs that copy OpenAI's
    wire format — OpenAI itself and Grok both do."""

    def __init__(self, base_url: str, api_key: str | None, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, query: str, citations: list[Citation]) -> str:
        prompt = build_prompt(query, citations)
        with httpx.Client(base_url=self._base_url, timeout=60.0) as client:
            response = client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
