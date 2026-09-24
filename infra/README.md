# radbrain local Compose stack

The default stack starts PostgreSQL/pgvector, Redis, MinIO, Keycloak, the web shell,
and clearly labelled API/worker placeholders. The placeholders expose only local
health/sleep behavior until the real Python services are built; they are not a
substitute for application code. The web image builds from `apps/web` as its
Docker context, so repository-level private study directories are never sent to
the Docker daemon.

PostgreSQL bootstraps a disposable superuser named `radbrain_bootstrap`. The
`002_roles.sh` init script creates `radbrain_migrator` and `radbrain_app`, makes
the migrator the database owner, and explicitly keeps the runtime role
`NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS`. The runtime role is not a
member of the migrator role. Run Alembic with `DATABASE_MIGRATOR_URL`, never
with the runtime URL.

`infra/compose/production.yml` is the production override used by the pull-only
deployment workflow. It requires `RADBRAIN_WEB_IMAGE` and removes the web build
section; the VPS must pull that immutable image rather than build it locally.

Copy `.env.example` to `.env` before using the stack. Never commit `.env` or
private study material.
