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

Interactive documentation is available at runtime:

- **Swagger UI:** `/docs`
- **ReDoc:** `/redoc`

Versioned OpenAPI spec: [`openapi/v1.yaml`](openapi/v1.yaml)

### Legacy endpoints

| Method | Path | Parameters | Description |
|---|---|---|---|
| `GET` | `/status` | — | DB health, row counts, regions, SKUs, last runs |
| `GET` | `/spot/eviction-rates` | `region?`, `sku_name?`, `job_id?`, `limit?` | Spot eviction rates (latest snapshot by default) |
| `GET` | `/spot/eviction-rates/history` | `limit?` | Available eviction rate snapshots |
| `GET` | `/spot/price-history` | `region?`, `sku_name?`, `os_type?`, `limit?` | Spot price history |

### V1 endpoints — Reference data

| Method | Path | Parameters | Description |
|---|---|---|---|
| `GET` | `/v1/status` | — | Database health and per-dataset statistics |
| `GET` | `/v1/locations` | `limit?`, `cursor?` | Distinct locations across all tables |
| `GET` | `/v1/skus` | `search?`, `limit?`, `cursor?` | Distinct SKU names |
| `GET` | `/v1/currencies` | `limit?`, `cursor?` | Distinct currency codes |
| `GET` | `/v1/os-types` | `limit?`, `cursor?` | Distinct OS types |
| `GET` | `/v1/stats` | — | Global dashboard metrics (counts, freshness) |

### V1 endpoints — Retail pricing

| Method | Path | Parameters | Description |
|---|---|---|---|
| `GET` | `/v1/retail/prices` | `region?`, `sku?`, `currency?`, `effectiveAt?`, `updatedSince?`, `snapshotDate?`, `limit?`, `cursor?` | Retail VM prices with filters |
| `GET` | `/v1/retail/prices/latest` | `region?`, `sku?`, `currency?`, `snapshotDate?`, `limit?`, `cursor?` | Latest retail price per unique key |
| `GET` | `/v1/retail/prices/compare` | `sku` *(required)*, `currency?`, `pricingType?`, `snapshotDate?` | Compare SKU retail price across all regions |
| `GET` | `/v1/retail/savings-plans` | `region?`, `sku?`, `currency?`, `snapshotDate?`, `limit?`, `cursor?` | Retail prices with savings plan data |

### V1 endpoints — Spot pricing

| Method | Path | Parameters | Description |
|---|---|---|---|
| `GET` | `/v1/spot/prices` | `region?`, `sku?`, `osType?`, `sample?`, `limit?`, `cursor?` | Spot price history (raw sampling) |
| `GET` | `/v1/spot/prices/series` | `region` *(req)*, `sku` *(req)*, `osType?`, `bucket?` | Spot price time series |
| `GET` | `/v1/spot/eviction-rates` | `region?`, `sku?`, `updatedSince?`, `snapshotDate?`, `limit?`, `cursor?` | Spot eviction rates |
| `GET` | `/v1/spot/eviction-rates/series` | `region` *(req)*, `sku` *(req)*, `bucket` *(req)*, `agg?` | Time-bucketed eviction rate aggregation |
| `GET` | `/v1/spot/eviction-rates/latest` | `region?`, `sku?`, `snapshotDate?`, `limit?` | Latest eviction rate per (region, sku) |
| `GET` | `/v1/spot/detail` | `region` *(req)*, `sku` *(req)*, `osType?`, `snapshotDate?` | Composite: spot price + eviction rate + SKU catalog |

### V1 endpoints — Pricing analytics

| Method | Path | Parameters | Description |
|---|---|---|---|
| `GET` | `/v1/pricing/categories` | `limit?`, `cursor?` | Distinct pricing categories |
| `GET` | `/v1/pricing/summary` | `region?[]`, `category?[]`, `priceType?[]`, `currency?`, `snapshotSince?`, `limit?`, `cursor?` | Pre-aggregated price summaries (multi-value filters) |
| `GET` | `/v1/pricing/summary/latest` | `region?[]`, `category?[]`, `priceType?[]`, `currency?`, `limit?`, `cursor?` | Price summaries from latest run |
| `GET` | `/v1/pricing/summary/series` | `region` *(req)*, `priceType` *(req)*, `bucket` *(req)*, `metric?`, `category?`, `currency?` | Time-bucketed pricing metric evolution |
| `GET` | `/v1/pricing/summary/cheapest` | `priceType?`, `metric?`, `category?`, `currency?`, `limit?` | Top N cheapest regions from latest run |
| `GET` | `/v1/pricing/summary/compare` | `regions[]` *(req)*, `priceType?`, `category?`, `currency?` | Compare pricing summaries across regions |

### V1 endpoints — SKU catalog

| Method | Path | Parameters | Description |
|---|---|---|---|
| `GET` | `/v1/skus/catalog` | `search?`, `category?`, `family?`, `minVcpus?`, `maxVcpus?`, `limit?`, `cursor?` | VM SKU catalog with filters |

### V1 endpoints — Operations

| Method | Path | Parameters | Description |
|---|---|---|---|
| `GET` | `/v1/jobs` | `dataset?`, `status?`, `limit?`, `cursor?` | Ingestion job runs (newest first) |
| `GET` | `/v1/jobs/{run_id}/logs` | `level?`, `limit?`, `cursor?` | Logs for a specific job run |

> All V1 endpoints support keyset pagination via `limit` (default 1000, max 5000) and `cursor` query parameters unless noted otherwise.

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
