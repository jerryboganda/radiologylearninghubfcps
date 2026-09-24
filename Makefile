SHELL := powershell.exe

.PHONY: up down check test typecheck lint migrate rls types security-scan

up:
	docker compose up -d
	docker compose ps

down:
	docker compose down

check:
	python -m ruff check apps packages evals scripts
	python -m mypy apps/api/app apps/worker/app
	python -m pytest -q apps/api/tests evals/checks/test_scaffolding.py
	npm --prefix apps/web run check
	npm --prefix apps/web test
	npm --prefix apps/web run build

test:
	python -m pytest -q

typecheck:
	python -m mypy apps/api/app apps/worker/app
	npm --prefix apps/web run check

lint:
	python -m ruff check apps packages
	npm --prefix apps/web run lint

migrate:
	python -m alembic -c alembic.ini upgrade head

rls:
	python -m pytest -q evals/checks/test_rls_live.py

types:
	python scripts/generate_openapi_types.py

security-scan:
	python -m bandit -r apps/api/app apps/worker/app
