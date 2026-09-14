# Decision log

## Database engine

We chose Postgres with the pgvector extension for the vector store.

It runs the same way locally (Docker Compose) and in the cloud (Neon), so
the application code never has to branch on where it's deployed.

## Deployment target

The application deploys to Azure Container Apps with minimum replicas set
to zero, so it never bills for idle compute between demo sessions.
