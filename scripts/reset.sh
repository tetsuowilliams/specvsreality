#!/usr/bin/env sh
# Stop the stack, wipe the Postgres volume, and rebuild (destructive).
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-specvsreality}"
POSTGRES_VOLUME="${COMPOSE_PROJECT_NAME}_pgdata"

echo "Stopping existing services..."
docker compose down --remove-orphans

echo "Removing ephemeral Postgres volume (${POSTGRES_VOLUME})..."
docker volume rm -f "${POSTGRES_VOLUME}" >/dev/null 2>&1 || true

echo "Starting services with a clean Postgres DB..."
exec "$ROOT/scripts/dev.sh"
