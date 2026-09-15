# Architecture notes

## Store module

The store module is the only part of the codebase that speaks SQL.
Every other module calls its functions instead of touching Postgres directly.

## Embeddings interface

Embeddings run behind an interface with one concrete implementation, Ollama.
This lets a different backend be added later without touching the code that calls it.

## Chunking strategy

A Markdown file is split into chunks along blank lines.
Each chunk keeps its exact line range, so a citation can point back to the source precisely.
