FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

FROM base AS prod
RUN pip install --no-cache-dir gunicorn
CMD ["gunicorn", "kingpi.app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]

FROM base AS dev
RUN pip install --no-cache-dir ".[dev]"
CMD ["uvicorn", "kingpi.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "src"]
