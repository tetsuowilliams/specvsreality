"""spec_version commit metadata; requirement evaluation and implements evidence

Revision ID: 20260521_0001
Revises: 20260514_0001
Create Date: 2026-05-21 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260521_0001"
down_revision: Union[str, Sequence[str], None] = "20260514_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "spec_version",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "spec_version",
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "spec_version",
        sa.Column("status", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "spec_version",
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE spec_version
            SET created_at = NOW() AT TIME ZONE 'UTC',
                status = 'active',
                commit_sha = 'unknown'
            WHERE created_at IS NULL
            """
        )
    )

    op.alter_column("spec_version", "created_at", nullable=False)
    op.alter_column("spec_version", "status", nullable=False)
    op.alter_column("spec_version", "commit_sha", nullable=False)

    op.add_column("requirement_version", sa.Column("implemented", sa.Boolean(), nullable=True))
    op.add_column("requirement_version", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "requirement_version",
        sa.Column("gaps", postgresql.ARRAY(sa.String()), nullable=True),
    )

    op.add_column("implements", sa.Column("evidence_file", sa.Text(), nullable=True))
    op.add_column("implements", sa.Column("evidence_line_number", sa.Integer(), nullable=True))
    op.add_column("implements", sa.Column("evidence_snippet", sa.Text(), nullable=True))
    op.add_column("implements", sa.Column("evidence_relevance", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("implements", "evidence_relevance")
    op.drop_column("implements", "evidence_snippet")
    op.drop_column("implements", "evidence_line_number")
    op.drop_column("implements", "evidence_file")
    op.drop_column("requirement_version", "gaps")
    op.drop_column("requirement_version", "summary")
    op.drop_column("requirement_version", "implemented")
    op.drop_column("spec_version", "commit_sha")
    op.drop_column("spec_version", "status")
    op.drop_column("spec_version", "committed_at")
    op.drop_column("spec_version", "created_at")
