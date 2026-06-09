# Contributing to SpecVsReality

Thank you for your interest in contributing!

## Development setup

### Docker (recommended)

```bash
./scripts/dev.sh
```

This copies `worker/.env.example` → `worker/.env` if needed, builds images, and starts the full stack.

### Hybrid local development

Run infrastructure in Docker, apps natively:

```bash
docker compose up -d postgres rabbitmq loki promtail grafana

uv sync
cp api/.env.example .env    # or api/.env — see note below
cp worker/.env.example worker/.env

export DATABASE_URL=postgresql+psycopg://specvsreality:specvsreality@localhost:5432/specvsreality
alembic -c repositories/alembic.ini upgrade head

# Terminal 1 — API
uv run uvicorn specvsreality_api.main:app --reload --port 8000

# Terminal 2 — worker
uv run specvsreality-worker

# Terminal 3 — frontend
cd frontend && cp .env.example .env && npm ci && npm run dev
```

Frontend dev server: http://localhost:5174

#### Environment file locations

- **Docker Compose:** `worker/.env` is loaded by the worker service.
- **Native API/worker:** Pydantic settings read `.env` relative to the process working directory. The VS Code workspace in `repo.code-workspace` uses the repo root as `cwd`, so place a root `.env` with `DATABASE_URL` and RabbitMQ settings, or export variables in your shell.

## Project structure

| Package | Path | Role |
|---------|------|------|
| `api` | `api/src/specvsreality_api/` | FastAPI HTTP API |
| `worker` | `worker/src/specvsreality_worker/` | RabbitMQ consumer, git adapter, AI agents |
| `messages` | `messages/src/specvsreality_messages/` | Shared queue message schemas |
| `repositories` | `repositories/src/` | SQLAlchemy models and Alembic migrations |
| `frontend` | `frontend/src/` | SvelteKit UI |

## Tests

```bash
# All Python tests (Docker required for integration tests)
uv run pytest

# Fast unit tests only
uv run pytest worker/tests/unit messages/tests

# Lint and typecheck
uv run ruff check .
uv run mypy

# Frontend
cd frontend && npm ci && npm test && npm run check
```

### Hello-world endpoint

`POST /hello-world` queues a `hello_world` message through RabbitMQ. It exists to verify API → queue → worker plumbing and is covered by tests. It is not used by the main UI.

### Worker message failures

If a handler raises an exception, the message is **nacked without requeue** and dropped. Check worker logs for failures.

## Code style

- Python: [ruff](https://docs.astral.sh/ruff/) for linting, [mypy](https://mypy-lang.org/) strict mode
- TypeScript/Svelte: `npm run check` (svelte-check)
- Line length: 100 characters (Python)

Optional local hooks:

```bash
uv run pre-commit install
```

## Pull requests

1. Fork and create a feature branch.
2. Run tests and lint locally.
3. Keep changes focused — one logical change per PR.
4. Update documentation if you change setup, env vars, or public API behavior.

## Migrations

Migrations live in `repositories/alembic/`. The API Docker container runs `alembic upgrade head` on startup. For hybrid dev, run migrations manually (see setup above).

Compose uses `pgvector/pgvector:pg16`. The current schema does not use vector columns; plain `postgres:16` also works for local development.
