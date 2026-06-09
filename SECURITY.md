# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

Please report security issues privately by opening a [GitHub security advisory](https://github.com/tetsuowilliams/specvsreality/security/advisories/new) or emailing the repository maintainer. Do not open public issues for undisclosed vulnerabilities.

We aim to acknowledge reports within a few business days.

## Local development posture

SpecVsReality v1 is designed for **trusted local development**:

- The **API has no authentication**. Any client that can reach the API can list repos, add repos, and queue worker jobs.
- **Docker Compose** publishes Postgres, RabbitMQ, Grafana, and the API on host ports with default credentials documented in [README.md](README.md).
- **`GIT_CLONE_TOKEN`** is injected at runtime for private repo cloning and is not written to logs on clone failure.

**Do not expose the default Docker Compose stack to untrusted networks or the public internet** without hardening (reverse proxy, authentication, rotated credentials, firewall rules).

## Secrets

- Never commit `.env` files. Only `.env.example` templates are tracked.
- Set `OPENAI_API_KEY` and other secrets in `worker/.env` locally.
