# knowledge-manager

Base de conocimiento personal sobre Markdown.
No es un chatbot de notas: recupera con citas, expone la salud del RAG (eval, no un script escondido) y se usa donde ya trabajas (CLI / MCP).

Gana en contrato + “no alucines y demuéstralo”, y en correr **gratis en Azure**.
Local (Compose, Ollama, watcher) es un perfil del mismo código, no otro producto.

## Estado

Recién arrancado. Sin código todavía.
El ciclo en curso (v0.1) es el índice con citas: FastAPI stateless, Postgres por URL, worker sobre tabla `jobs`. Todavía sin LLM de respuesta.

## Problema

Las notas se acumulan y no se consultan.
Un grep no responde “¿qué decidimos sobre X y dónde está escrito?”.
Un chat sin citas inventa.
Un reindex manual convierte el hábito en laboratorio.

## Propósito

- Azure-gratis primero: Container Apps con scale to zero, Neon + pgvector, sin disco del contenedor como almacén.
- Contrato y evidencia: citas (ruta + fragmento); sin evidencia, negativa explícita; eval visible.
- Local como alternativa: Compose + Ollama + watcher de carpeta, mismo binario.

## Cómo funciona (visión)

1. **Ingesta:** `POST /index` encola un job; el worker parte, embebe y escribe en pgvector. En local, un watcher puede encolar solo.
2. **Recuperación:** pregunta → fragmentos con citas. Fuera de corpus → negativa.
3. **Respuesta (opcional):** LLM configurable (Claude, Grok, OpenAI, Ollama). Sin clave, no hay generación.
4. **Salud del RAG:** eval de groundedness, trazas por `ask`, prompt versionado.

Hoy solo existe la intención.

## Qué no es

No es Obsidian ni un wiki, ni un wrapper de un solo vendor, ni una consola React.
OpenAI no es un plan gratis: la demo Azure tiene que vivir sin esa clave.

## Audiencia

Quien escribe las notas (CLI/MCP) y quien mira una URL de demo (Azure + dummy).

## Stack

Python 3.10+. FastAPI, Postgres+pgvector, tabla `jobs`, pytest, OpenAPI.
Local: Docker Compose + Ollama. Azure: Container Apps + Neon. Embeddings in-process en la nube.
Detalle en `ki/project/vision/VISION.md`.

## Roadmap

1. **v0.1** — API, Neon-ready Postgres, ingesta, citas, jobs; watcher solo local.
2. **v0.2** — Ask con proveedor configurable, eval, LLMOps-lite, MCP, `write_note`.
3. **v0.3** — URL en Azure (ACA scale to zero + Neon + dummy).

## Licencia

MIT. Copyright (c) 2026 rdorta27.
