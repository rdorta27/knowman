# How to test

## Automated tests

```bash
uv run pytest -v
```

They run against a separate test database (`<db>_test`, never the development one — it is created on first use). The ones that need Postgres skip themselves when none is reachable.

```bash
uv run ruff check .
uv run black --check .
```

## Retrieval (search with citations)

```bash
docker compose exec api knowman search "why Postgres"          # should cite decision-log.md
docker compose exec api knowman search "capital of mongolia"   # should be the explicit negative
```

## Ask (generated answer)

With no provider configured, `ask` behaves like `search` — citations only, nothing invented:

```bash
docker compose exec api knowman ask "why Postgres"
```

With a provider (local Ollama, no key needed):

```bash
docker compose exec -e LLM_PROVIDER=ollama api knowman ask "why Postgres"
```

## Watcher (add, change, delete without running anything)

```bash
echo -e "# Test\n\nSomething new." > corpus/dummy/test.md
sleep 3
docker compose exec api knowman search "something new"   # should find it

rm corpus/dummy/test.md
sleep 3
docker compose exec api knowman search "something new"   # should return the negative again
```

## Eval (retrieval health)

```bash
docker compose exec api knowman eval
```

Runs the 25 questions in `eval/dataset.json`, reports groundedness without depending on any language model, and the delta against the previous run. A drop is a real signal: this is what caught a chunking bug where a lone heading became its own chunk and matched unrelated questions.

## Agent (`knowman write`)

Needs `qwen3.5:2b` pulled in Ollama (`AGENT_MODEL`). The smaller `qwen3.5:0.8b` used by `ask` is not reliable at tool-calling — don't use it here:

```bash
docker compose exec api knowman write "take a note that we decided to use SQLite for the local cache"
```

A new `.md` should appear under the corpus and be indexed without running `ingest` by hand:

```bash
docker compose exec api knowman search "SQLite for the local cache"
```

## Ask traces

```bash
docker exec -it $(docker compose ps -q db) psql -U knowman -d knowman \
  -c "SELECT id, prompt_id, citation_count, has_citation, latency_ms, tokens_approx, answered FROM traces ORDER BY id DESC LIMIT 5;"
```

## Indexing jobs over HTTP

```bash
curl -X POST http://localhost:8000/index
curl http://localhost:8000/index/1
```

## Every HTTP endpoint

Interactive Swagger UI: `http://localhost:8000/docs`.
