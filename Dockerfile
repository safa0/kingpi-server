FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/

RUN adduser --disabled-password --no-create-home appuser
USER appuser

FROM base AS prod
USER root
RUN pip install --no-cache-dir gunicorn
USER appuser
CMD ["gunicorn", "kingpi.app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]

FROM base AS dev
USER root
RUN pip install --no-cache-dir ".[dev]"
USER appuser
CMD ["uvicorn", "kingpi.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "src"]
