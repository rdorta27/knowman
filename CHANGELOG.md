# Changelog

Newest first. Each entry matches a released tag.

## v0.2.4 — 2026-09-15

- The install works on a machine it has never run on: it names the right package for your distribution, checks that Docker actually answers before starting, and fails with a fix rather than a stack trace.
- Inference runs on the GPU wherever the hardware allows it, through Vulkan, and on CPU everywhere else with nothing to configure.
- The container now builds as your own user, so a notes folder mounted from the host stays writable.
- Settings from `.env` reach every service; before, the worker and the API could disagree about which embeddings model they used.
- The API is published on localhost only, like every other service.
- Tests cover settings, every CLI command, and the install script itself.

## v0.2.3 — 2026-09-15

- `knowman write <instruction>` runs an agent that can search the index and write a new note, indexed the moment it lands.
- A filename that would escape the notes folder is rejected before anything is written.

## v0.2.2 — 2026-09-15

- Every `ask` call is recorded with its citations, latency, token estimate, and prompt version.
- Prompt text moved out of the code into versioned files: changing the wording means adding a file, not editing Python.
- An MCP server exposes `search` and `ask` as read-only tools over stdio, for any MCP client.
- Structured JSON logging replaced plain text in the API and worker.

## v0.2.1 — 2026-09-15

- `knowman eval` and `GET /eval` score 25 labeled questions against retrieval — deterministic, with no model judging another model.
- Every run is stored and compared against the previous one, so a regression shows up as a drop.
- Fixed a chunking bug the eval itself caught: a lone heading became its own chunk and matched unrelated questions once the corpus grew.

## v0.2.0 — 2026-09-15

- `ask` answers in three states: an explicit negative with no evidence, citations alone with no provider ready, and a generated answer with its citations when one is.
- Ollama, Claude, OpenAI, and Grok are interchangeable providers; the paid three speak plain HTTP, with no vendor SDKs added.
- The embedding dimension is detected from the configured model instead of hardcoded, so switching models no longer breaks the schema.

## v0.1.5 — 2026-09-14

- `install.sh` brings up the whole stack on a fresh machine, pulls the embeddings model, seeds the sample notes, and proves a real search returns a real citation.
- It never installs anything itself: missing prerequisites come with the command to fix them.

## v0.1.4 — 2026-09-14

- Services are no longer reachable from outside localhost.
- Containers run as a non-root user, and the notes mount is read-only wherever nothing writes.
- A failed job no longer leaks raw exception text over HTTP.

## v0.1.3 — 2026-09-14

- Documentation covering installation, every CLI command, and every HTTP endpoint, with examples.

## v0.1.2 — 2026-09-14

- A watcher turns every note added, edited, or deleted into an indexing job, so no citation outlives its source.
- A worker runs those jobs, and `POST /index` with `GET /index/{id}` exposes the same lifecycle over HTTP.
- One `docker compose up` starts the database, Ollama, the API, the worker, and the watcher together.

## v0.1.1 — 2026-09-14

- `knowman search` returns citations from the CLI, and `GET /search` mirrors the same contract over HTTP.
- A configurable distance threshold decides what counts as evidence; no match is an explicit negative, never a guess.

## v0.1.0 — 2026-09-14

- Markdown notes are parsed, split into chunks that keep their line ranges, embedded, and stored.
- Re-indexing is idempotent: running it again never duplicates anything.
- Runs locally through Docker Compose, with Ollama for embeddings.
