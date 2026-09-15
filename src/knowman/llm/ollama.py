import httpx

from knowman.llm.base import LLMProvider, build_prompt
from knowman.retrieval import Citation


class OllamaChat(LLMProvider):
    def __init__(self, url: str, model: str) -> None:
        self._url = url.rstrip("/")
        self._model = model

    def is_available(self) -> bool:
        return True

    def generate(self, query: str, citations: list[Citation]) -> str:
        prompt = build_prompt(query, citations)
        with httpx.Client(base_url=self._url, timeout=120.0) as client:
            response = client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    # Reasoning models (e.g. qwen3.x) otherwise put the answer
                    # in a separate "thinking" field and leave content empty.
                    "think": False,
                },
            )
            response.raise_for_status()
            message = response.json()["message"]
            return message.get("content") or message.get("thinking", "")
