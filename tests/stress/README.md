# Stress Tests

Validate KingPi server atomicity and correctness under concurrent load using [hey](https://github.com/rakyll/hey).

## Prerequisites

- `hey` installed: `brew install hey` or `go install github.com/rakyll/hey@latest`
- App stack running in **production** mode: `make prod`
- Docker containers (postgres, redis) accessible via `docker compose exec`

> **Important:** Always test against the prod compose target (multi-worker uvicorn). The dev target uses `--reload` with a single worker and is not representative.

## Atomicity Test

Fires N concurrent POST requests and verifies the event counter matches exactly.

```bash
# Default: 100 concurrent requests
bash tests/stress/test_atomicity.sh

# Custom count
bash tests/stress/test_atomicity.sh 500
```

### What It Does

1. Flushes Redis and truncates Postgres `package_events` table
2. Fires N fully concurrent POST requests via `hey`
3. Queries the event total from the API
4. Compares successful POSTs against the actual total — exits non-zero on mismatch

### Environment Variables

| Variable           | Default                  | Description          |
|--------------------|--------------------------|----------------------|
| `KINGPI_BASE_URL`  | `http://localhost:8000`  | Server base URL      |

## Monitoring

While tests run, monitor resource usage in separate terminals:

```bash
# Container CPU and memory
docker stats

# PostgreSQL active connections
docker compose exec postgres psql -U kingpi -d kingpi -c "SELECT count(*) FROM pg_stat_activity;"

# Redis stats
docker compose exec redis redis-cli INFO stats
docker compose exec redis redis-cli INFO clients
```
