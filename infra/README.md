# radbrain local Compose stack

The default stack starts PostgreSQL/pgvector, Redis, RustFS, Keycloak, the web shell,
the real FastAPI process, the real Celery worker, and a one-shot migration job. The
runtime containers receive the RLS-bound app role; only the migration job receives
`DATABASE_MIGRATOR_URL`. The web image builds from `apps/web` as its Docker context,
and the repository root `.dockerignore` excludes private study directories and local
caches. These controls are part of the local safety boundary.

PostgreSQL bootstraps a disposable superuser named `radbrain_bootstrap`. The
`002_roles.sh` init script creates `radbrain_migrator` and `radbrain_app`, makes
the migrator the database owner, and explicitly keeps the runtime role
`NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS`. The runtime role is not a
member of the migrator role. Run Alembic with `DATABASE_MIGRATOR_URL`, never
with the runtime URL.

`infra/compose/production.yml` is the production override used by the pull-only
deployment workflow. It requires immutable `RADBRAIN_MIGRATOR_IMAGE`,
`RADBRAIN_API_IMAGE`, `RADBRAIN_WORKER_IMAGE`, `RADBRAIN_STORAGE_IMAGE`, and
`RADBRAIN_WEB_IMAGE` references and removes all local build sections; the
deployment host must pull those images rather than build them locally.

Copy `.env.example` to `.env` before using the stack. Never commit `.env` or
private study material.
