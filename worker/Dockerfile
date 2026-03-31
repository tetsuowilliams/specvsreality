# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.12-bookworm

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY messages ./messages
COPY worker ./worker
COPY repositories ./repositories
COPY api ./api

RUN uv sync --frozen --no-dev --package specvsreality-worker

ENV PATH="/app/.venv/bin:$PATH"

CMD ["specvsreality-worker"]
