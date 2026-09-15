from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://knowman:knowman@localhost:5432/knowman"
    embeddings_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    embeddings_model: str = "qwen3-embedding:0.6b"
    retrieval_max_distance: float = 0.5
    retrieval_default_k: int = 3
    corpus_path: str = "corpus/dummy"

    llm_provider: str | None = None
    chat_model: str = "qwen3.5:0.8b"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    xai_api_key: str | None = None
    xai_model: str = "grok-4"

    prompt_version: str = "ask_v1"


def get_settings() -> Settings:
    return Settings()
