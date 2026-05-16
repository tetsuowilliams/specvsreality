"""Alembic environment: sync URL from config or `DATABASE_URL`."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

# Ensure `src` is on path when running `alembic` from `repositories/` without install
_repo_root = Path(__file__).resolve().parents[1]
_src = _repo_root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from alembic import context
from sqlalchemy import create_engine, pool

# Import models so metadata is populated
from specvsreality_repositories.models import artifact as _artifact  # noqa: F401, E402
from specvsreality_repositories.models import artifact_version as _artifact_version  # noqa: F401, E402
from specvsreality_repositories.models import git_repo as _git_repo  # noqa: F401, E402
from specvsreality_repositories.models import implements as _implements  # noqa: F401, E402
from specvsreality_repositories.models import requirement as _requirement  # noqa: F401, E402
from specvsreality_repositories.models import requirement_version as _requirement_version  # noqa: F401, E402
from specvsreality_repositories.models import spec as _spec  # noqa: F401, E402
from specvsreality_repositories.models import spec_version as _spec_version  # noqa: F401, E402
from specvsreality_repositories.models.base import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url") or ""
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql+psycopg2"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
