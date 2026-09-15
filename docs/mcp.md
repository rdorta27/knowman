# Conectar MCP

`knowman mcp` corre un servidor [MCP](https://modelcontextprotocol.io) por stdio, con dos tools de solo lectura:

- `search(query, k?)` — mismo contrato que `knowman search` / `GET /search`.
- `ask(query, k?)` — mismo contrato que `knowman ask` / `POST /ask`.

Un servidor MCP local no corre como servicio (no vive en `docker compose`) — el cliente lo lanza como subproceso cada vez que lo necesita.

## Requisitos

El comando corre sobre el entorno Python del host (`uv run knowman mcp`), no dentro de un contenedor. Necesita:

```bash
uv sync
```

Y que `db`/`ollama` estén levantados y accesibles en `localhost` (los puertos ya están publicados así por `docker-compose.yml`):

```bash
docker compose up -d db ollama
```

Con el `.env.example` por default (`DATABASE_URL`/`OLLAMA_URL` apuntando a `localhost`), no hace falta configurar nada más.

## Probar el servidor solo, sin cliente

```bash
echo '' | timeout 3 uv run knowman mcp; echo "exit=$?"
```

`exit=0` confirma que arranca y cierra limpio — no verifica el protocolo en sí, para eso hace falta un cliente MCP real.

## Configurar en Claude Code

Agregar (o editar) `.mcp.json` en la raíz del repo:

```json
{
  "mcpServers": {
    "knowman": {
      "command": "uv",
      "args": ["run", "--directory", "/ruta/absoluta/al/repo", "knowman", "mcp"]
    }
  }
}
```

Reiniciar la sesión de Claude Code. El servidor `knowman` debería aparecer con las tools `search` y `ask` disponibles para usar directamente en la conversación, sin copiar/pegar nada del índice.

## Configurar en Claude Desktop

Mismo formato, en `claude_desktop_config.json` (Settings → Developer → Edit Config).

## Troubleshooting

- **El cliente no encuentra el comando `uv`**: usar la ruta absoluta a `uv` en `command`, o a `knowman` dentro del `.venv` (`/ruta/al/repo/.venv/bin/knowman`) sin pasar por `uv run`.
- **Timeouts o "no evidence"**: confirmar que `db`/`ollama` están corriendo y que el corpus fue ingestado (`knowman ingest` — ver `docs/running.md`).
- **`ask` no genera respuesta**: sin `LLM_PROVIDER` configurado en el entorno, `ask` se comporta como `search` — esperado, no es un error.
