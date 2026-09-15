# Connecting an MCP client

`knowman mcp` runs an [MCP](https://modelcontextprotocol.io) server over stdio with two read-only tools:

- `search(query, k?)` — the same contract as `knowman search` and `GET /search`.
- `ask(query, k?)` — the same contract as `knowman ask` and `POST /ask`.

A local MCP server is not a service: it doesn't live in `docker compose`. The client launches it as a subprocess whenever it needs it.

## Requirements

The command runs on the host's Python environment (`uv run knowman mcp`), not inside a container. It needs:

```bash
uv sync
```

And `db` and `ollama` running and reachable on `localhost` (the ports are already published that way by `docker-compose.yml`):

```bash
docker compose up -d db ollama
```

With the defaults in `.env.example` (`DATABASE_URL` and `OLLAMA_URL` pointing at `localhost`), nothing else needs configuring.

## Testing the server without a client

```bash
echo '' | timeout 3 uv run knowman mcp; echo "exit=$?"
```

`exit=0` confirms it starts and shuts down cleanly. It does not verify the protocol itself — that needs a real MCP client.

## Configuring it in Claude Code

Add (or edit) `.mcp.json` in the repository root:

```json
{
  "mcpServers": {
    "knowman": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/knowman", "knowman", "mcp"]
    }
  }
}
```

Restart the session. The `knowman` server should appear with `search` and `ask` available directly in the conversation, with nothing copied and pasted out of the index.

## Configuring it in Claude Desktop

Same format, in `claude_desktop_config.json` (Settings → Developer → Edit Config).

## Troubleshooting

- **The client can't find `uv`**: use the absolute path to `uv` in `command`, or point at `knowman` inside the virtualenv (`/path/to/knowman/.venv/bin/knowman`) and skip `uv run`.
- **Timeouts or "no evidence"**: confirm `db` and `ollama` are running and that the corpus was indexed (`knowman ingest` — see `running.md`).
- **`ask` returns no generated answer**: without `LLM_PROVIDER` set in the environment, `ask` behaves like `search`. That is expected, not a failure.
