# radbrain local Compose stack

The default stack starts PostgreSQL/pgvector, Redis, MinIO, Keycloak, the web shell,
and clearly labelled API/worker placeholders. The placeholders expose only local
health/sleep behavior until the real Python services are built; they are not a
substitute for application code. The web image builds from `apps/web` as its
Docker context, so repository-level private study directories are never sent to
the Docker daemon.

Copy `.env.example` to `.env` before using the stack. Never commit `.env` or
private study material.
