#!/bin/sh
set -e

case "${KINGPI_ENV:-dev}" in
  prod)
    exec gunicorn kingpi.app:app \
      -w "${KINGPI_WORKERS:-4}" \
      -k uvicorn.workers.UvicornWorker \
      -b 0.0.0.0:8000
    ;;
  dev-multi)
    exec uvicorn kingpi.app:app \
      --host 0.0.0.0 \
      --port 8000 \
      --workers "${KINGPI_WORKERS:-4}"
    ;;
  *)
    exec uvicorn kingpi.app:app \
      --host 0.0.0.0 \
      --port 8000 \
      --reload \
      --reload-dir src
    ;;
esac
