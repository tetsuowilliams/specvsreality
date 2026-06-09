# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-06-08

### Added

- Initial open-source release
- Docker Compose stack: API, worker, frontend, Postgres, RabbitMQ, Loki, Promtail, Grafana
- `./scripts/dev.sh` one-command local startup
- Worker message pipeline: `init_repo` → `wind_to_head` → `spec_scan`
- AI agents for spec extraction, artifact candidate detection, and implementation checks
- SvelteKit frontend for repo and spec dashboards
- GitHub Actions CI for lint, typecheck, and tests

### Security

- Documented local-only API posture (no authentication in v1)
