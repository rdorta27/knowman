# Roadmap notes

## Current cycle

The current cycle adds asking questions with a configurable LLM provider, measuring groundedness, and exposing the index through MCP.

## LLM providers

Claude, OpenAI, and Grok all work over plain HTTP, with no extra SDK dependency.
Ollama runs locally and needs no API key at all.

## Next cycle

The next cycle deploys the project to Azure Container Apps, with minimum replicas set to zero so it never bills for idle time.
