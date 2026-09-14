from fastapi import FastAPI

from knowman.config import get_settings

app = FastAPI(title="knowman", version="0.1.0")


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "embeddings_provider": settings.embeddings_provider}
