# SpecVsReality

Track whether your implementation matches your specifications. SpecVsReality watches Git repositories for `specs/` folders, walks commit history, and uses AI agents to compare specs against the codebase.

## Quick start

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) with Compose v2.

```bash
git clone https://github.com/tetsuowilliams/specvsreality.git
cd specvsreality
./scripts/dev.sh
```

Then open **http://localhost:8080**.

| Service | URL | Default credentials |
|---------|-----|---------------------|
| Frontend | http://localhost:8080 | — |
| API | http://localhost:8000 | — |
| RabbitMQ management | http://localhost:15672 | guest / guest |
| Grafana | http://localhost:3000 | admin / admin |

To wipe the database and rebuild from scratch: `./scripts/reset.sh`

## First run

1. Start the stack with `./scripts/dev.sh`.
2. Open the frontend and **add a repository** (public Git URL).
3. Set `OPENAI_API_KEY` in `worker/.env` (copied automatically from `worker/.env.example` on first run).
4. Restart the worker: `docker compose restart worker`
5. Watch progress: `docker compose logs -f worker`

The database starts empty — there is no bundled demo data.

### Repository layout

Tracked repositories must contain specs under `specs/`:

```
specs/
  0001-my-feature/
    spec.md       # required
    plan.md       # optional
    tasks.md      # optional
```

## Architecture

```
Frontend → API → RabbitMQ → Worker → Git clones
                ↓              ↓
             Postgres ←───────┘
```

When you add a repo, the worker runs a three-stage pipeline:

1. **init_repo** — clone the repository
2. **wind_to_head** — sync commits and detect spec changes
3. **spec_scan** — run AI agents to extract specs and find implementation candidates

## Configuration

| File | Purpose |
|------|---------|
| `worker/.env` | Worker secrets and AI model settings (required for Docker Compose) |
| `api/.env.example` | API settings for hybrid local dev |
| `frontend/.env.example` | `PUBLIC_API_BASE_URL` for native frontend dev |

### Required for AI scanning

- `OPENAI_API_KEY` in `worker/.env`

### Optional

- `GIT_CLONE_TOKEN` — clone private repositories (passed from host shell into compose)
- `LOGFIRE_TOKEN` or `OPIK_URL_OVERRIDE` — LLM tracing (see `worker/.env.example`)

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for hybrid local development, running tests, and code style.

### Run tests

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy

cd frontend && npm ci && npm test && npm run check
```

Integration tests require Docker (testcontainers).

## Security

This project is intended for **local development**. The API has no authentication, and Docker Compose exposes services with default credentials on host ports. **Do not expose the default stack to the public internet.**

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## License

[MIT](LICENSE)
