from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://knowman:knowman@localhost:5432/knowman"
    embeddings_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    embeddings_model: str = "nomic-embed-text"


def get_settings() -> Settings:
    return Settings()
