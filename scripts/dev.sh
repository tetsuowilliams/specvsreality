#!/usr/bin/env sh
# Start the full SpecVsReality stack in Docker (non-destructive).
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker is not installed or not on PATH" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "error: docker daemon is not running" >&2
  exit 1
fi

if [ ! -f worker/.env ]; then
  echo "Creating worker/.env from worker/.env.example..."
  cp worker/.env.example worker/.env
fi

if ! grep -E '^OPENAI_API_KEY=.+' worker/.env >/dev/null 2>&1; then
  echo ""
  echo "warning: OPENAI_API_KEY is not set in worker/.env."
  echo "         The stack will start, but spec scanning will not run until you add a key"
  echo "         and restart the worker: docker compose restart worker"
  echo ""
fi

echo "Building and starting services..."
docker compose up --build -d

echo "Waiting for API health..."
TRIES=0
MAX_TRIES=60
until curl -sf http://localhost:8800/health >/dev/null 2>&1; do
  TRIES=$((TRIES + 1))
  if [ "$TRIES" -ge "$MAX_TRIES" ]; then
    echo "error: API did not become healthy within ${MAX_TRIES}s" >&2
    echo "Check logs: docker compose logs api" >&2
    exit 1
  fi
  sleep 2
done

cat <<EOF

SpecVsReality is running.

  Frontend:  http://localhost:9080
  API:       http://localhost:8800  (health: /health)
  RabbitMQ:  http://localhost:15672  (guest / guest)
  Grafana:   http://localhost:3000   (admin / admin)

Next steps:
  1. Open the frontend and add a Git repository (public URL with specs/ layout).
  2. Set OPENAI_API_KEY in worker/.env for AI scanning, then: docker compose restart worker
  3. Follow worker logs: docker compose logs -f worker

To wipe the database and rebuild: ./scripts/reset.sh
EOF
