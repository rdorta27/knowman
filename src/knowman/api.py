from datetime import datetime
from importlib.resources import files

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from knowman.access import RateLimitMiddleware, require_token
from knowman.ask import ask as run_ask
from knowman.config import get_settings
from knowman.dashboard import build_file_list, build_status
from knowman.embeddings import get_embeddings_provider
from knowman.eval import load_dataset
from knowman.eval import run_eval as run_eval_dataset
from knowman.llm import get_llm_provider
from knowman.logging_setup import configure_json_logging, get_logger
from knowman.retrieval import Citation
from knowman.retrieval import search as retrieval_search
from knowman.store import JobSummary, Store, Trace

configure_json_logging()
logger = get_logger("knowman.api")

if get_settings().api_token:
    logger.info("startup", extra={"extra_fields": {"auth": "token required"}})
else:
    logger.warning("startup", extra={"extra_fields": {"auth": "open — API_TOKEN is unset"}})

app = FastAPI(title="knowman", version="0.1.0")
app.add_middleware(RateLimitMiddleware)


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


class AskRequest(BaseModel):
    q: str
    k: int | None = None


class AskResponse(BaseModel):
    citations: list[CitationResponse]
    answer: str | None


class EvalResponse(BaseModel):
    groundedness: float
    total: int
    correct: int
    answered_count: int | None
    delta: float | None
    failing: list[str]


class EvalRunSummary(BaseModel):
    id: int
    created_at: datetime
    groundedness: float
    total: int
    correct: int
    answered_count: int | None


class JobSummaryResponse(BaseModel):
    id: int
    type: str
    status: str
    updated_at: datetime
    error: str | None

    @classmethod
    def from_job(cls, job: JobSummary) -> "JobSummaryResponse":
        return cls(
            id=job.id, type=job.type, status=job.status, updated_at=job.updated_at, error=job.error
        )


class TraceResponse(BaseModel):
    id: int
    created_at: datetime
    query: str
    citation_count: int
    answered: bool
    latency_ms: float

    @classmethod
    def from_trace(cls, trace: Trace) -> "TraceResponse":
        return cls(
            id=trace.id,
            created_at=trace.created_at,
            query=trace.query,
            citation_count=trace.citation_count,
            answered=trace.answered,
            latency_ms=trace.latency_ms,
        )


class EvalHistoryResponse(BaseModel):
    runs: list[EvalRunSummary]


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "embeddings_provider": settings.embeddings_provider}


@app.get("/search", dependencies=[Depends(require_token)])
def search(q: str, k: int | None = None) -> SearchResponse:
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    resolved_k = k if k is not None else settings.retrieval_default_k
    citations = retrieval_search(q, store, embeddings, resolved_k, settings.retrieval_max_distance)
    logger.info("search", extra={"extra_fields": {"query": q, "citation_count": len(citations)}})
    return SearchResponse(citations=[CitationResponse.from_citation(c) for c in citations])


@app.post("/ask", dependencies=[Depends(require_token)])
def ask(request: AskRequest) -> AskResponse:
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    llm_provider = get_llm_provider(settings)
    resolved_k = request.k if request.k is not None else settings.retrieval_default_k
    result = run_ask(
        request.q, store, embeddings, llm_provider, resolved_k, settings.retrieval_max_distance
    )
    logger.info(
        "ask",
        extra={
            "extra_fields": {
                "query": request.q,
                "citation_count": len(result.citations),
                "answered": result.answer is not None,
            }
        },
    )
    return AskResponse(
        citations=[CitationResponse.from_citation(c) for c in result.citations],
        answer=result.answer,
    )


@app.get("/eval", dependencies=[Depends(require_token)])
def get_eval() -> EvalResponse:
    settings = get_settings()
    store = Store(settings.database_url)
    embeddings = get_embeddings_provider(settings)
    llm_provider = get_llm_provider(settings)
    dataset = load_dataset()
    result = run_eval_dataset(
        dataset,
        store,
        embeddings,
        llm_provider,
        settings.retrieval_default_k,
        settings.retrieval_max_distance,
    )
    return EvalResponse(
        groundedness=result.groundedness,
        total=result.total,
        correct=result.correct,
        answered_count=result.answered_count,
        delta=result.delta,
        failing=[r.id for r in result.results if not r.correct],
    )


@app.get("/eval/history", dependencies=[Depends(require_token)])
def get_eval_history(limit: int = 20) -> EvalHistoryResponse:
    settings = get_settings()
    store = Store(settings.database_url)
    runs = store.list_eval_runs(limit=limit)
    return EvalHistoryResponse(
        runs=[
            EvalRunSummary(
                id=r.id,
                created_at=r.created_at,
                groundedness=r.groundedness,
                total=r.total,
                correct=r.correct,
                answered_count=r.answered_count,
            )
            for r in runs
        ]
    )


@app.post("/index", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_token)])
def enqueue_index() -> IndexJobResponse:
    settings = get_settings()
    store = Store(settings.database_url)
    job_id = store.enqueue_job("ingest_path", {"path": settings.corpus_path})
    logger.info("index enqueued", extra={"extra_fields": {"job_id": job_id}})
    return IndexJobResponse(job_id=job_id)


@app.get("/index/{job_id}", dependencies=[Depends(require_token)])
def get_index_job(job_id: int) -> JobStatusResponse:
    settings = get_settings()
    store = Store(settings.database_url)
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    error = "job failed" if job.status == "failed" else None
    return JobStatusResponse(id=job.id, status=job.status, error=error)


# --- Monitoring panel -----------------------------------------------------
# GET /dashboard serves the static page with no token: it's inert markup,
# useless without data. Every route it calls is protected like any other.

_DASHBOARD_HTML = files("knowman") / "static" / "dashboard.html"


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(_DASHBOARD_HTML)


@app.get("/status", dependencies=[Depends(require_token)])
def get_status() -> dict:
    settings = get_settings()
    store = Store(settings.database_url)
    return build_status(settings, store)


@app.get("/files", dependencies=[Depends(require_token)])
def get_files() -> list[dict]:
    settings = get_settings()
    store = Store(settings.database_url)
    return build_file_list(settings, store)


@app.get("/jobs/recent", dependencies=[Depends(require_token)])
def get_recent_jobs(limit: int = 20) -> list[JobSummaryResponse]:
    settings = get_settings()
    store = Store(settings.database_url)
    return [JobSummaryResponse.from_job(j) for j in store.list_recent_jobs(limit)]


@app.get("/traces/recent", dependencies=[Depends(require_token)])
def get_recent_traces(limit: int = 20) -> list[TraceResponse]:
    settings = get_settings()
    store = Store(settings.database_url)
    return [TraceResponse.from_trace(t) for t in store.list_traces(limit)]
