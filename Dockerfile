FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

RUN adduser --disabled-password --no-create-home appuser
USER appuser

FROM base AS prod
USER root
RUN pip install --no-cache-dir gunicorn
USER appuser
# Run migrations before starting — ensures schema is up to date.
# Safe to run repeatedly: Alembic tracks applied revisions and skips already-applied ones.
CMD ["sh", "-c", "alembic upgrade head && gunicorn kingpi.app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000"]

FROM base AS dev
USER root
RUN pip install --no-cache-dir ".[dev]"
USER appuser
CMD ["sh", "-c", "alembic upgrade head && uvicorn kingpi.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir src"]
