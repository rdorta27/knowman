# Levantar el servidor

## Máquina nueva

```bash
git clone <este repositorio>
cd knowledge-manager
./install.sh
```

Verifica `git`/`docker`/`docker compose`, construye la imagen, levanta todo, baja el modelo de embeddings, aplica el schema, ingesta el corpus dummy y confirma que `knowman search` devuelve una cita real. Si falta algo, imprime cómo instalarlo y no continúa.

## Manual (ya instalado)

```bash
docker compose up --build -d
```

Levanta cinco servicios:

| Servicio | Qué hace |
| --- | --- |
| `db` | Postgres + pgvector |
| `ollama` | embeddings y chat locales (in-container) |
| `api` | FastAPI en `http://localhost:8000` |
| `worker` | consume la tabla `jobs`, cada 2s |
| `watcher` | observa `corpus/dummy/` y encola jobs al crear/editar/borrar un `.md` |

Primera vez (o después de cambiar `EMBEDDINGS_MODEL`/`CHAT_MODEL`):

```bash
docker compose exec ollama ollama pull qwen3-embedding:0.6b
docker compose exec ollama ollama pull qwen3.5:0.8b   # solo si vas a usar LLM_PROVIDER=ollama
docker compose exec api knowman db-init
docker compose exec api knowman ingest
```

## Reconstruir después de cambiar código

```bash
docker compose up --build -d
```

Si cambiaste algo que toca el schema (una tabla nueva, el modelo de embeddings), volvé a correr `knowman db-init`. Si cambiaste el modelo de embeddings, también `knowman ingest` (los vectores viejos quedan en otro espacio vectorial, hay que reindexar).

## Ver logs

```bash
docker compose logs api --tail=50
docker compose logs worker --tail=50
```

Ambos emiten JSON estructurado (una línea por request/job), no texto libre.

## Bajar todo

```bash
docker compose down        # mantiene los volúmenes (datos, modelos de Ollama)
docker compose down -v     # borra también los volúmenes — arranque realmente limpio
```
