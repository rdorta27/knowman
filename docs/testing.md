# Cómo probar

## Tests automatizados

```bash
uv run pytest -v
```

Corren contra una base de test separada (`<db>_test`, no la de desarrollo — se crea sola la primera vez). Los que necesitan Postgres se saltan solos si no hay uno alcanzable.

```bash
uv run ruff check .
uv run black --check .
```

## Retrieval (búsqueda con citas)

```bash
docker compose exec api knowman search "por qué Postgres"     # debería citar decision-log.md
docker compose exec api knowman search "capital of mongolia"  # debería ser la negativa explícita
```

## Ask (respuesta generada)

Sin proveedor configurado, `ask` se comporta como `search` (solo citas, sin inventar):

```bash
docker compose exec api knowman ask "por qué Postgres"
```

Con un proveedor (ej. Ollama local, sin clave necesaria):

```bash
docker compose exec -e LLM_PROVIDER=ollama api knowman ask "por qué Postgres"
```

## Watcher (alta / cambio / baja sin tocar nada a mano)

```bash
echo -e "# Prueba\n\nAlgo nuevo." > corpus/dummy/prueba.md
sleep 3
docker compose exec api knowman search "algo nuevo"   # debería encontrarlo

rm corpus/dummy/prueba.md
sleep 3
docker compose exec api knowman search "algo nuevo"   # debería volver a la negativa
```

## Eval (salud del RAG)

```bash
docker compose exec api knowman eval
```

Corre las 25 preguntas de `eval/dataset.json`, reporta groundedness (sin depender de ningún LLM) y el delta contra la corrida anterior. Si el groundedness baja, es señal real de una regresión — es lo que atrapó el bug de chunking en `v0.2.1`.

## Agente (`knowman write`)

Necesita `qwen3.5:2b` bajado en Ollama (`AGENT_MODEL`) — `qwen3.5:0.8b` (el de `ask`) es demasiado chico para tool-calling confiable, no lo uses acá:

```bash
docker compose exec api knowman write "toma nota de que decidimos usar SQLite para el caché local"
```

Debería aparecer un `.md` nuevo bajo `corpus/dummy/` y quedar indexado sin correr `ingest` a mano:

```bash
docker compose exec api knowman search "SQLite para el caché"
```

## Trazas de `ask`

```bash
docker exec -it $(docker compose ps -q db) psql -U knowman -d knowman \
  -c "SELECT id, prompt_id, citation_count, has_citation, latency_ms, tokens_approx, answered FROM traces ORDER BY id DESC LIMIT 5;"
```

## Jobs de indexado por HTTP

```bash
curl -X POST http://localhost:8000/index
curl http://localhost:8000/index/1
```

## Endpoints HTTP en general

Swagger interactivo: `http://localhost:8000/docs`.
