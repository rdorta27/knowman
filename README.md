# knowledge-manager

Base de conocimiento personal sobre Markdown.
No es un chatbot de notas: recupera con citas, expone la salud del RAG (eval, no un script escondido) y se usa donde ya trabajas (CLI / MCP).

Gana en contrato + “no alucines y demuéstralo”, y en correr **gratis en Azure**.
Local (Compose, Ollama, watcher) es un perfil del mismo código, no otro producto.

## Estado

v0.2 — preguntar con proveedor configurable: ingesta, retrieval con citas por CLI/HTTP/MCP, jobs, watcher local, `ask` con proveedor opcional, eval de groundedness y un agente que escribe notas.

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

`install.sh` verifica que `git`, `docker` y el plugin `docker compose` estén instalados y que el daemon de Docker sea alcanzable (si falta algo, imprime cómo resolverlo según tu gestor de paquetes y no continúa — nunca instala nada con privilegios por su cuenta). Si el host tiene `/dev/dri`, activa la GPU por Vulkan; si no, todo corre en CPU sin configurar nada. Si todo está, levanta el stack completo, baja el modelo de embeddings, indexa el corpus dummy y confirma que `knowman search` devuelve una cita real. No requiere Python ni `uv` en el host — todo corre dentro de los contenedores.

Más detalle operativo en `docs/`: [levantar el servidor](docs/running.md), [cómo probar cada pieza](docs/testing.md), [conectar un cliente MCP](docs/mcp.md).

## Instalación y uso (manual)

Requiere Docker y Docker Compose.

```bash
git clone <este repositorio>
cd knowledge-manager
docker compose up --build
```

Esto levanta cuatro servicios sobre la misma imagen (más Postgres, cinco en total):

| Servicio | Qué hace |
| --- | --- |
| `db` | Postgres + pgvector |
| `ollama` | embeddings locales (in-container, no depende del host) |
| `api` | FastAPI en `http://localhost:8000` |
| `worker` | consume la tabla `jobs`, cada 2s |
| `watcher` | observa `corpus/dummy/` y encola jobs al crear/editar/borrar un `.md` |

La primera vez hay que bajar el modelo de embeddings dentro del contenedor de Ollama:

```bash
docker compose exec ollama ollama pull qwen3-embedding:0.6b
```

A partir de ahí, cualquier `.md` que agregues, edites o borres en `corpus/dummy/` se refleja solo en el índice — no hace falta correr nada a mano.

### CLI

Con el entorno Python local (`uv sync`) y `DATABASE_URL`/`OLLAMA_URL` apuntando a los servicios de arriba (ver `.env.example`):

| Comando | Qué hace |
| --- | --- |
| `knowman db-init` | aplica el schema (`jobs`, y `chunks` con la dimensión del modelo de embeddings configurado) |
| `knowman ingest [--path DIR]` | ingesta un directorio o un archivo `.md` (default: `corpus_path` de la config) |
| `knowman search <query> [--k N]` | busca y devuelve citas en texto plano, o una negativa explícita |
| `knowman ask <query> [--k N]` | como `search`, pero si hay un proveedor LLM configurado genera una respuesta citando el contexto |
| `knowman eval` | corre `eval/dataset.json` (25 preguntas), reporta groundedness y el delta contra la corrida anterior |
| `knowman worker` | corre el worker en primer plano (lo que hace el servicio `worker`) |
| `knowman watch [--path DIR]` | corre el watcher en primer plano (lo que hace el servicio `watcher`) |
| `knowman mcp` | corre un servidor MCP por stdio, con las tools `search` y `ask` |
| `knowman write <instrucción>` | agente (LangGraph + Ollama) que puede buscar y/o escribir una nota nueva en el corpus, en lenguaje natural |

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
| `POST /ask` | body `{"q": str, "k": int?}` → `{"citations": [...], "answer": str \| null}` — `answer` es `null` sin evidencia o sin proveedor LLM listo |
| `GET /eval` | corre el dataset de eval al momento, devuelve groundedness, delta y las preguntas que fallaron |
| `GET /eval/history?limit=` | corridas de eval pasadas, más nueva primero |
| `POST /index` | encola un job de ingesta sobre `corpus_path`, devuelve `{"job_id": N}` (202) |
| `GET /index/{id}` | estado del job: `pending` / `processing` / `done` / `failed`, con `error` si falló |

### MCP

`knowman mcp` corre un servidor [MCP](https://modelcontextprotocol.io) por stdio, con dos tools de solo lectura: `search` y `ask` (mismo contrato que sus equivalentes de CLI/HTTP). Un cliente MCP lo lanza como subproceso local, por ejemplo en Claude Code (`.mcp.json`):

```json
{
  "mcpServers": {
    "knowman": {
      "command": "uv",
      "args": ["run", "--directory", "/ruta/al/repo", "knowman", "mcp"]
    }
  }
}
```

### Variables de entorno

Ver `.env.example`. Las más relevantes:

| Variable | Default | Qué es |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://knowman:knowman@localhost:5432/knowman` | Postgres+pgvector |
| `OLLAMA_URL` | `http://localhost:11434` | endpoint de embeddings |
| `EMBEDDINGS_MODEL` | `qwen3-embedding:0.6b` | modelo de embeddings de Ollama — cambiarlo exige correr `db-init` y `ingest` de nuevo (dimensión y espacio vectorial distintos) |
| `CORPUS_PATH` | `corpus/dummy` | directorio que ingesta/observa la app |
| `RETRIEVAL_MAX_DISTANCE` | `0.5` | umbral de distancia coseno; por encima, no cuenta como evidencia |
| `RETRIEVAL_DEFAULT_K` | `3` | cantidad de citas por consulta |
| `LLM_PROVIDER` | _(sin definir)_ | `ollama` / `claude` / `openai` / `grok` — sin definir, `ask` solo hace retrieval |
| `CHAT_MODEL` | `qwen3.5:0.8b` | modelo de chat de Ollama (si `LLM_PROVIDER=ollama`) |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | _(sin clave)_ / `claude-sonnet-5` | clave y modelo para `LLM_PROVIDER=claude` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | _(sin clave)_ / `gpt-4o-mini` | clave y modelo para `LLM_PROVIDER=openai` |
| `XAI_API_KEY` / `XAI_MODEL` | _(sin clave)_ / `grok-4` | clave y modelo para `LLM_PROVIDER=grok` |
| `PROMPT_VERSION` | `ask_v1` | qué archivo de `prompts/` usa `ask` — cambiar el texto es agregar un archivo, no tocar código |
| `AGENT_MODEL` | `qwen3.5:2b` | modelo de Ollama que usa `knowman write` — necesita soporte de tool-calling; `CHAT_MODEL` (más chico) no alcanza para esto |

## Arquitectura

- **`store`** — única puerta a Postgres+pgvector (psycopg + SQL crudo). Nada más en el código escribe SQL; cambiar de motor vectorial algún día significa reescribir este módulo, no el resto.
- **`embeddings`** — interfaz con una implementación (Ollama). Pensada para agregar un proveedor in-process en Azure sin tocar quien la llama.
- **`chunking` / `ingest`** — parte un `.md` en fragmentos citables por rango de líneas, los embebe y los persiste; acepta un archivo o un directorio.
- **`retrieval`** — embebe una consulta, filtra los resultados de `store.search` por un umbral de distancia; una lista vacía es la negativa explícita.
- **`llm` / `ask`** — `llm` es la interfaz de proveedor LLM (Ollama sin clave; Claude/OpenAI/Grok con clave, por HTTP directo sin SDKs). `ask` combina `retrieval` + `llm`: sin evidencia → negativa; con evidencia pero sin proveedor listo → solo citas; con evidencia y proveedor listo → respuesta generada + citas. El texto del prompt vive en `prompts/` (no en el código), versionado por archivo; cada llamada a `ask` queda registrada en `traces` (citas, latencia, tokens aproximados, si generó respuesta y con qué versión de prompt).
- **`logging_setup`** — logs de `api` y `worker` en JSON estructurado (stdlib `logging`, sin dependencia nueva), una línea por request/job.
- **`mcp_server`** — servidor MCP por stdio (SDK oficial), expone `search` y `ask` como tools de solo lectura sobre la misma lógica que la CLI/HTTP.
- **`eval`** — corre `eval/dataset.json` (25 preguntas etiquetadas como "debe citar de X" o "debe ser negativa") contra `retrieval`; groundedness es el % de aciertos, sin LLM de por medio. Cada corrida queda guardada (`eval_runs`), así se puede comparar contra la anterior.
- **`agent`** — agente LangGraph (ReAct) sobre Ollama con dos tools: `search_notes` (misma lógica que `retrieval`) y `write_note` (escribe un `.md` nuevo dentro de `corpus_path` — rechaza cualquier nombre que se salga del directorio — y lo indexa al toque). Cada paso del agente queda logueado en JSON. Solo Ollama por ahora, sin exponerse por MCP.
- **`worker` / `watcher`** — el worker consume la tabla `jobs` (`ingest_path`, `delete_path`); el watcher (solo perfil local, no existe en Azure) traduce eventos de filesystem en esos mismos jobs.
- **`api` / `cli`** — dos clientes sobre la misma lógica: la CLI es el camino feliz local, la API es el hábito público en Azure.

`api` y `worker` corren desde la misma imagen Docker (`Dockerfile`), con distinto comando — en Azure, ese es literalmente el contrato: el mismo contenedor sirve de servicio HTTP (Container Apps) y de Job de ingesta.

### Seguridad (v0.1.4)

- Ninguna query de `store` concatena SQL: todo pasa por parámetros bindeados (`%s`), sin excepciones.
- `db`, `ollama` y `api` publican su puerto solo en `127.0.0.1`, no en todas las interfaces — no alcanzables desde la red.
- Los contenedores corren con un usuario sin privilegios, no como root.
- El volumen del corpus se monta de solo lectura en `worker` y `watcher` — ninguno de los dos escribe archivos. `api` lo monta con escritura desde `v0.2.3`, porque `knowman write` (el agente) necesita crear notas ahí.
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
