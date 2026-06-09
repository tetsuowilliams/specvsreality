# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.12-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY messages ./messages
COPY worker ./worker
COPY repositories ./repositories
COPY api ./api

RUN uv sync --frozen --no-dev --package specvsreality-worker

ENV PATH="/app/.venv/bin:$PATH"

CMD ["specvsreality-worker"]
