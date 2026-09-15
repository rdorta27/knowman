# Security notes

## Container user

The application containers run as an unprivileged user, not root.
This limits the damage of any single compromised process.

## Exposed ports

The database and the embeddings service only publish their ports on localhost.
Neither is reachable from another machine on the network.

## Error messages

A failed indexing job never returns its raw exception text over HTTP.
The full error stays in the database, for local debugging only.
