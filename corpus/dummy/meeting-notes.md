# Weekly sync notes

## Retrieval quality

The team agreed that any answer without a citation counts as no answer.
Retrieval must return the source path and the exact line range it drew
from, so a claim can be checked against the original note by hand.

## Next steps

Ingestion needs to be idempotent: running it twice over the same corpus
must not create duplicate chunks in the store.
