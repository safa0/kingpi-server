FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .
RUN pip install --no-cache-dir gunicorn

COPY src/ src/

ENV PYTHONPATH=/app/src

RUN adduser --disabled-password --no-create-home appuser
USER appuser
