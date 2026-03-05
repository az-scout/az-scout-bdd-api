# Copilot Instructions for az-scout-bdd-api

## Project overview

Standalone REST API serving Azure VM SKU pricing, spot eviction, and availability data from PostgreSQL. Deployed as an Azure Container App.

## Tech stack

- **Backend:** Python 3.11+, FastAPI 0.115+, uvicorn, psycopg 3.2+ (async), psycopg_pool
- **Database:** PostgreSQL 17+ (Azure Flexible Server or local Docker)
- **Auth:** Password or Azure Managed Identity (MSI) via azure-identity
- **Packaging:** hatchling + hatch-vcs, CalVer, src-layout
- **Tools:** uv (package manager), ruff (lint + format), mypy (strict), pytest

## Project structure

```
src/az_scout_bdd_api/
├── __init__.py       # Package init
├── config.py         # DatabaseConfig + env var loader
├── db.py             # Async psycopg pool manager
├── db_api.py         # All SQL query functions
├── pagination.py     # Keyset cursor pagination
├── routes.py         # 25+ FastAPI endpoints (legacy + /v1/)
└── validation.py     # Input validators and enums
api/
├── main.py           # FastAPI app bootstrap
├── Dockerfile        # Container build
└── requirements.txt  # Runtime dependencies
openapi/
└── v1.yaml           # OpenAPI spec (source of truth)
tests/
├── test_api_v1.py    # API endpoint tests
└── test_pagination.py # Pagination tests
```

## Code conventions

- All functions must have type annotations (`disallow_untyped_defs = true`).
- Follow ruff rules: `E, F, I, W, UP, B, SIM`. Line length is 100.
- Use `from __future__ import annotations` when needed.
- No global mutable state except the DB pool singleton.

## Database patterns

- All DB access goes through `db.py` (async pool) and `db_api.py` (SQL queries).
- Auth supports password and Azure MSI (`POSTGRES_AUTH_METHOD`).
- Keyset pagination via `pagination.py` for large result sets.
- All query functions accept cursor/limit params for pagination.

## Testing patterns

- Tests use FastAPI's `TestClient` (httpx).
- DB functions are mocked with `unittest.mock.patch`.
- Run with: `uv run pytest`

## Quality checks

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
```
