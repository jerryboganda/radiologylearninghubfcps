# radbrain

Source-controlled implementation of the FCPS Radiology Brain OS specification.

The project is a provenance-first, tenant-isolated radiology study platform with a
SvelteKit PWA, FastAPI API, Celery workers, PostgreSQL/pgvector, Redis, and
S3-compatible object storage.

## Development

Requirements:

- Python 3.12+
- Node.js 24 and npm
- Docker Desktop/Engine with Compose v2 (required for the complete stack)

```powershell
Copy-Item .env.example .env
make up
make check
```

The API can be exercised without Docker using development adapters:

```powershell
python -m apps.api.app.main
```

The local study material under `Radiology Exam Material/` and `Radiology Images/`
is intentionally ignored by Git. It must not be committed or uploaded to public
fixtures. See `docs/runbooks/data-handling.md` before using it for local tests.

See `docs/SPEC.md` and `docs/decisions/` for product and architectural decisions.
