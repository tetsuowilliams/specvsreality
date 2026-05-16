#!/usr/bin/env sh

set -eu

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-specvsreality}"
POSTGRES_VOLUME="${COMPOSE_PROJECT_NAME}_pgdata"
SEED_DEMO_DATA_ON_REDEPLOY="${SEED_DEMO_DATA_ON_REDEPLOY:-1}"

echo "Stopping existing services..."
docker compose down --remove-orphans

echo "Removing ephemeral Postgres volume (${POSTGRES_VOLUME})..."
docker volume rm -f "${POSTGRES_VOLUME}" >/dev/null 2>&1 || true

echo "Starting services with a clean Postgres DB..."
SEED_DEMO_DATA_ON_REDEPLOY="${SEED_DEMO_DATA_ON_REDEPLOY}" docker compose up --build -d

echo "Services are up. Follow logs with: docker compose logs -f"
