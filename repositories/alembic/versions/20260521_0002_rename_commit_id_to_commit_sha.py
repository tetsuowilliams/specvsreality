"""Rename commit_id to commit_sha on version tables

Revision ID: 20260521_0002
Revises: 20260521_0001
Create Date: 2026-05-21 00:02:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260521_0002"
down_revision: Union[str, Sequence[str], None] = "20260521_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("artifact_version", "commit_id", new_column_name="commit_sha")
    op.alter_column("requirement_version", "commit_id", new_column_name="commit_sha")


def downgrade() -> None:
    op.alter_column("requirement_version", "commit_sha", new_column_name="commit_id")
    op.alter_column("artifact_version", "commit_sha", new_column_name="commit_id")
