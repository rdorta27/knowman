# knowledge-manager

Base de conocimiento personal sobre Markdown.
No es un chatbot de notas: recupera con citas, expone la salud del RAG (eval, no un script escondido) y se usa donde ya trabajas (CLI / MCP).

Gana en contrato + “no alucines y demuéstralo”, y en correr **gratis en Azure**.
Local (Compose, Ollama, watcher) es un perfil del mismo código, no otro producto.

## Estado

v0.1 — índice con citas (v0.1.0-v0.1.2 entregados): ingesta, retrieval con citas por CLI/HTTP, jobs, watcher local.
Todavía sin LLM de respuesta (`ask`) — eso es v0.2.

## Problema

Las notas se acumulan y no se consultan.
Un grep no responde “¿qué decidimos sobre X y dónde está escrito?”.
Un chat sin citas inventa.
Un reindex manual convierte el hábito en laboratorio.

## Propósito

- Azure-gratis primero: Container Apps con scale to zero, Neon + pgvector, sin disco del contenedor como almacén.
- Contrato y evidencia: citas (ruta + fragmento); sin evidencia, negativa explícita; eval visible.
- Local como alternativa: Compose + Ollama + watcher de carpeta, mismo binario.

## Instalación en una máquina nueva

```bash
git clone <este repositorio>
cd knowledge-manager
./install.sh
```

`install.sh` verifica que `git`, `docker` y el plugin `docker compose` estén instalados (si falta alguno, imprime cómo instalarlo según tu gestor de paquetes y no continúa — nunca instala nada con privilegios por su cuenta). Si todo está, levanta el stack completo, baja el modelo de embeddings, indexa el corpus dummy y confirma que `knowman search` devuelve una cita real. No requiere Python ni `uv` en el host — todo corre dentro de los contenedores.

## Instalación y uso (manual)

Requiere Docker y Docker Compose.

```bash
git clone <este repositorio>
cd knowledge-manager
docker compose up --build
```

Esto levanta cuatro servicios sobre la misma imagen (más Postgres):

| Servicio | Qué hace |
| --- | --- |
| `db` | Postgres + pgvector |
| `ollama` | embeddings locales (in-container, no depende del host) |
| `api` | FastAPI en `http://localhost:8000` |
| `worker` | consume la tabla `jobs`, cada 2s |
| `watcher` | observa `corpus/dummy/` y encola jobs al crear/editar/borrar un `.md` |

La primera vez hay que bajar el modelo de embeddings dentro del contenedor de Ollama:

```bash
docker compose exec ollama ollama pull nomic-embed-text
```

A partir de ahí, cualquier `.md` que agregues, edites o borres en `corpus/dummy/` se refleja solo en el índice — no hace falta correr nada a mano.

### CLI

Con el entorno Python local (`uv sync`) y `DATABASE_URL`/`OLLAMA_URL` apuntando a los servicios de arriba (ver `.env.example`):

| Comando | Qué hace |
| --- | --- |
| `knowman db-init` | aplica el schema (tablas `chunks`, `jobs`) |
| `knowman ingest [--path DIR]` | ingesta un directorio o un archivo `.md` (default: `corpus_path` de la config) |
| `knowman search <query> [--k N]` | busca y devuelve citas en texto plano, o una negativa explícita |
| `knowman worker` | corre el worker en primer plano (lo que hace el servicio `worker`) |
| `knowman watch [--path DIR]` | corre el watcher en primer plano (lo que hace el servicio `watcher`) |

Ejemplo:

```bash
uv run knowman search "por qué Postgres"
# decision-log.md:L5-L5
#   We chose Postgres with the pgvector extension for the vector store.
```

### HTTP

OpenAPI interactivo en `http://localhost:8000/docs`.

| Endpoint | Qué hace |
| --- | --- |
| `GET /health` | liveness, sin tocar la base |
| `GET /search?q=&k=` | mismo contrato que la CLI, responde `{"citations": [...]}` (vacío si no hay evidencia) |
| `POST /index` | encola un job de ingesta sobre `corpus_path`, devuelve `{"job_id": N}` (202) |
| `GET /index/{id}` | estado del job: `pending` / `processing` / `done` / `failed`, con `error` si falló |

### Variables de entorno

Ver `.env.example`. Las más relevantes:

| Variable | Default | Qué es |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://knowman:knowman@localhost:5432/knowman` | Postgres+pgvector |
| `OLLAMA_URL` | `http://localhost:11434` | endpoint de embeddings |
| `EMBEDDINGS_MODEL` | `nomic-embed-text` | modelo de Ollama |
| `CORPUS_PATH` | `corpus/dummy` | directorio que ingesta/observa la app |
| `RETRIEVAL_MAX_DISTANCE` | `0.5` | umbral de distancia coseno; por encima, no cuenta como evidencia |
| `RETRIEVAL_DEFAULT_K` | `3` | cantidad de citas por consulta |

## Arquitectura

- **`store`** — única puerta a Postgres+pgvector (psycopg + SQL crudo). Nada más en el código escribe SQL; cambiar de motor vectorial algún día significa reescribir este módulo, no el resto.
- **`embeddings`** — interfaz con una implementación (Ollama). Pensada para agregar un proveedor in-process en Azure sin tocar quien la llama.
- **`chunking` / `ingest`** — parte un `.md` en fragmentos citables por rango de líneas, los embebe y los persiste; acepta un archivo o un directorio.
- **`retrieval`** — embebe una consulta, filtra los resultados de `store.search` por un umbral de distancia; una lista vacía es la negativa explícita.
- **`worker` / `watcher`** — el worker consume la tabla `jobs` (`ingest_path`, `delete_path`); el watcher (solo perfil local, no existe en Azure) traduce eventos de filesystem en esos mismos jobs.
- **`api` / `cli`** — dos clientes sobre la misma lógica: la CLI es el camino feliz local, la API es el hábito público en Azure.

`api` y `worker` corren desde la misma imagen Docker (`Dockerfile`), con distinto comando — en Azure, ese es literalmente el contrato: el mismo contenedor sirve de servicio HTTP (Container Apps) y de Job de ingesta.

### Seguridad (v0.1.4)

- Ninguna query de `store` concatena SQL: todo pasa por parámetros bindeados (`%s`), sin excepciones.
- `db` y `ollama` publican su puerto solo en `127.0.0.1`, no en todas las interfaces — no alcanzables desde la red.
- Los contenedores corren con un usuario sin privilegios, no como root.
- El volumen del corpus se monta de solo lectura en `api`, `worker` y `watcher`.
- `GET /index/{id}` nunca devuelve el detalle crudo de una excepción; el mensaje completo queda solo en la base (columna `jobs.error`), para debug local.
- No hay autenticación ni rate limiting en ningún endpoint — decisión deliberada mientras la API solo escucha en `localhost`; se revisita al exponerla en Azure (v0.3).

## Qué no es

No es Obsidian ni un wiki, ni un wrapper de un solo vendor, ni una consola React.
OpenAI no es un plan gratis: la demo Azure tiene que vivir sin esa clave.

## Audiencia

Quien escribe las notas (CLI/MCP) y quien mira una URL de demo (Azure + dummy).

## Stack

Python 3.11+. FastAPI, Postgres+pgvector, tabla `jobs`, pytest, OpenAPI.
Local: Docker Compose + Ollama. Azure: Container Apps + Neon. Embeddings in-process en la nube.
Detalle en `ki/project/vision/VISION.md`.

## Roadmap

1. **v0.1** — API, Neon-ready Postgres, ingesta, citas, jobs, watcher local. En curso: documentación, revisión de seguridad, instalación en máquina nueva.
2. **v0.2** — Ask con proveedor configurable, eval, LLMOps-lite, MCP, `write_note`.
3. **v0.3** — URL en Azure (ACA scale to zero + Neon + dummy).

## Licencia

MIT. Copyright (c) 2026 rdorta27.
