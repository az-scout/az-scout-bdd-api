# az-scout-bdd-api

Standalone REST API serving Azure VM SKU pricing, spot eviction, and availability data from PostgreSQL.

## Architecture

```
Plugin (az-scout-plugin-bdd-sku)
    ↓ HTTP
API (this repo) ← PostgreSQL ← Ingestion (az-scout-bdd-ingestion)
```

- **This repo** exposes 25+ read-only FastAPI endpoints (legacy + `/v1/`)
- **PostgreSQL** is the data store (Azure Flexible Server or local Docker)
- **[az-scout-bdd-ingestion](https://github.com/rsabile/az-scout-bdd-ingestion)** populates the database
- **[az-scout-plugin-bdd-sku](https://github.com/rsabile/az-scout-plugin-bdd-sku)** is the az-scout plugin that proxies to this API

## Prerequisites

- Python 3.11+
- PostgreSQL 17+ (Azure Flexible Server or [local via Docker Compose](https://github.com/rsabile/az-scout-bdd-ingestion))
- Database populated by [az-scout-bdd-ingestion](https://github.com/rsabile/az-scout-bdd-ingestion)

## Quick start

```bash
# Install dependencies
uv sync

# Configure database connection
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=azscout
export POSTGRES_USER=azscout
export POSTGRES_PASSWORD=azscout

# Run the API
uvicorn api.main:app --reload --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `azscout` | Database name |
| `POSTGRES_USER` | `azscout` | Database user |
| `POSTGRES_PASSWORD` | `azscout` | Database password |
| `POSTGRES_SSLMODE` | `disable` | SSL mode (`require` for Azure) |
| `POSTGRES_AUTH_METHOD` | `password` | Auth method: `password` or `msi` |
| `AZURE_CLIENT_ID` | *(empty)* | User-assigned Managed Identity client ID (when `msi`) |

## Docker

```bash
docker build -f api/Dockerfile -t az-scout-bdd-api .
docker run -p 8000:8000 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_DB=azscout \
  -e POSTGRES_USER=azscout \
  -e POSTGRES_PASSWORD=azscout \
  az-scout-bdd-api
```

## API reference

The API serves Swagger UI at `/docs` and ReDoc at `/redoc`.

Versioned OpenAPI spec: [`openapi/v1.yaml`](openapi/v1.yaml)

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Quality checks
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
```

## License

See [LICENSE.txt](LICENSE.txt).
