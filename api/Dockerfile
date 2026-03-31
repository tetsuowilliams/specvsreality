# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.12-bookworm

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY messages ./messages
COPY repositories ./repositories
COPY api ./api
COPY worker ./worker

RUN uv sync --frozen --no-dev --package specvsreality-api

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["sh", "-c", "alembic -c /app/repositories/alembic.ini upgrade head && exec uvicorn specvsreality_api.main:app --host 0.0.0.0 --port 8000"]
