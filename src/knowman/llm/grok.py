from knowman.llm._openai_compatible import OpenAICompatibleProvider


class GrokProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str | None, model: str) -> None:
        super().__init__(base_url="https://api.x.ai/v1", api_key=api_key, model=model)
