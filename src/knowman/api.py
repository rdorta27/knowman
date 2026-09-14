from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from knowman.config import get_settings
from knowman.embeddings import get_embeddings_provider
from knowman.retrieval import Citation
from knowman.retrieval import search as retrieval_search
from knowman.store import Store

app = FastAPI(title="knowman", version="0.1.0")


class IndexJobResponse(BaseModel):
    job_id: int


class JobStatusResponse(BaseModel):
    id: int
    status: str
    error: str | None


class CitationResponse(BaseModel):
    path: str
    line_start: int
    line_end: int
    text: str
    distance: float

    @classmethod
    def from_citation(cls, citation: Citation) -> "CitationResponse":
        return cls(
            path=citation.path,
            line_start=citation.line_start,
            line_end=citation.line_end,
            text=citation.text,
            distance=citation.distance,
        )


class SearchResponse(BaseModel):
    citations: list[CitationResponse]


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "embeddings_provider": settings.embeddings_provider}


@app.get("/search")
def search(q: str, k: int | None = None) -> SearchResponse:
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    resolved_k = k if k is not None else settings.retrieval_default_k
    citations = retrieval_search(q, store, embeddings, resolved_k, settings.retrieval_max_distance)
    return SearchResponse(citations=[CitationResponse.from_citation(c) for c in citations])


@app.post("/index", status_code=status.HTTP_202_ACCEPTED)
def enqueue_index() -> IndexJobResponse:
    settings = get_settings()
    store = Store(settings.database_url)
    job_id = store.enqueue_job("ingest_path", {"path": settings.corpus_path})
    return IndexJobResponse(job_id=job_id)


@app.get("/index/{job_id}")
def get_index_job(job_id: int) -> JobStatusResponse:
    settings = get_settings()
    store = Store(settings.database_url)
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    error = "job failed" if job.status == "failed" else None
    return JobStatusResponse(id=job.id, status=job.status, error=error)
