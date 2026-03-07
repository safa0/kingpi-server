# KingPi Server

Lightweight PyPI analytics proxy server.

## Prerequisites

- Python 3.12+
- PostgreSQL
- Redis

## Running with Docker (preferred)

```bash
# Dev mode (hot reload)
docker compose --profile dev up --build

# Multi-worker mode
docker compose --profile dev-multi up --build

# Production
KINGPI_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db docker compose --profile prod up --build
```

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn kingpi.app:app --reload
```

## Environment variables

| Variable | Default |
|---|---|
| `KINGPI_DATABASE_URL` | `postgresql+asyncpg://kingpi:kingpi@localhost:5432/kingpi` |
| `KINGPI_REDIS_URL` | `redis://localhost:6379/0` |
| `KINGPI_DEBUG` | `false` |
| `KINGPI_PYPI_CACHE_TTL_SECONDS` | `300` |
| `KINGPI_PYPI_REQUEST_TIMEOUT_SECONDS` | `10.0` |
| `KINGPI_API_PREFIX` | `/api/v1` |

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe (checks DB + Redis) |
| `POST` | `/api/v1/event` | Record install/uninstall event |
| `GET` | `/api/v1/package/{name}` | Package info + event stats |
| `GET` | `/api/v1/package/{name}/event/{type}/total` | Event count |
| `GET` | `/api/v1/package/{name}/event/{type}/last` | Last event timestamp |

## Tests

```bash
pytest                        # unit tests
pytest -m integration         # integration tests (needs running services)
```

## Linting

```bash
ruff check src/ tests/
```
