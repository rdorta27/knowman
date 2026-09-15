import httpx

from knowman.llm.base import LLMProvider, build_prompt
from knowman.retrieval import Citation

_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, query: str, citations: list[Citation]) -> str:
        prompt = build_prompt(query, citations)
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                _API_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": _ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]
