-- Initial schema: the vector extension and the jobs queue table.
-- Applied by `knowman db-init`. Re-running is safe (IF NOT EXISTS).
-- chunks isn't here: its embedding column's width depends on the
-- configured embeddings model, detected at runtime (see Store.init_schema).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eval_runs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    groundedness DOUBLE PRECISION NOT NULL,
    total INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    answered_count INTEGER,
    results JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS traces (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    prompt_id TEXT,
    query TEXT NOT NULL,
    citation_count INTEGER NOT NULL,
    has_citation BOOLEAN NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    tokens_approx INTEGER NOT NULL,
    answered BOOLEAN NOT NULL
);
