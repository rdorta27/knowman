# Running the stack

## On a new machine

```bash
git clone https://github.com/radorta27/knowman
cd knowman
./install.sh
```

It checks `git`, `docker`, and `docker compose`, confirms the Docker daemon answers, builds the image, starts everything, pulls the embeddings model, applies the schema, indexes the sample corpus, and confirms `knowman search` returns a real citation. If anything is missing, it prints how to fix it and stops.

## Configuration (`.env`)

```bash
cp .env.example .env
```

Docker Compose reads `.env` on its own, with no flag to pass: it substitutes those values into `docker-compose.yml` before starting anything. The same file is read by `uv run knowman ...` when you run on the host.

Two details that trip people up:

- `DATABASE_URL` and `OLLAMA_URL` point at `localhost` because that is what running on the host needs. Inside the containers, Compose replaces them with the service names (`db`, `ollama`), so editing them there changes nothing about the stack.
- `KNOWMAN_UID` and `KNOWMAN_GID` must match your own user (`id -u`, `id -g`). The corpus is mounted from the host and the agent writes into it; if they don't match, `knowman write` fails on permissions.

After changing `.env`, run `docker compose up -d --build`.

## GPU (optional)

If the host exposes `/dev/dri`, `install.sh` enables the GPU on its own by writing this line into `.env`:

```
COMPOSE_FILE=docker-compose.yml:docker-compose.gpu.yml
```

That passes the device to Ollama and allows integrated GPUs (`OLLAMA_IGPU_ENABLE=1`). To force CPU, comment the line out and bring the stack back up.

Without a GPU there is nothing to configure: Ollama runs on CPU by itself. To confirm which one is in use:

```bash
docker compose logs ollama | grep "inference compute"
```

## Manual start (already installed)

```bash
docker compose up --build -d
```

That starts five services:

| Service | What it does |
| --- | --- |
| `db` | Postgres + pgvector |
| `ollama` | local embeddings and chat, in-container |
| `api` | FastAPI on `http://localhost:8000` |
| `worker` | polls the `jobs` table every 2s |
| `watcher` | watches the corpus and enqueues jobs when a `.md` file changes |

First time (or after changing `EMBEDDINGS_MODEL` or `CHAT_MODEL`):

```bash
docker compose exec ollama ollama pull qwen3-embedding:0.6b
docker compose exec ollama ollama pull qwen3.5:0.8b   # only if you plan to use LLM_PROVIDER=ollama
docker compose exec api knowman db-init
docker compose exec api knowman ingest
```

## Rebuilding after a code change

```bash
docker compose up --build -d
```

If the change touches the schema (a new table, a different embeddings model), run `knowman db-init` again. If it was the embeddings model, run `knowman ingest` too: the old vectors live in a different vector space and have to be rebuilt.

## Logs

```bash
docker compose logs api --tail=50
docker compose logs worker --tail=50
```

Both emit structured JSON, one line per request or job, not free text.

## Shutting down

```bash
docker compose down        # keeps the volumes (index data, Ollama models)
docker compose down -v     # drops the volumes too — a genuinely clean start
```
