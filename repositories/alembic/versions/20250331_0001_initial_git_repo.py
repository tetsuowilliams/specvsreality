"""initial schema

Revision ID: 20250331_0001
Revises:
Create Date: 2025-03-31 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250331_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "git_repo",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("cursor_position", sa.String(length=64), nullable=False),
        sa.Column("location", sa.String(length=4096), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "spec",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("paper_id", sa.String(length=255), nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["git_repo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "spec_version",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spec_id", sa.Integer(), nullable=False),
        sa.Column("spec_md", sa.Text(), nullable=False),
        sa.Column("tasks_md", sa.Text(), nullable=False),
        sa.Column("plan_md", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["spec_id"], ["spec.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "requirement",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spec_id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["spec_id"], ["spec.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "artifact",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("filepath", sa.String(length=4096), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "artifact_version",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("artifact_id", sa.Integer(), nullable=False),
        sa.Column("commit_id", sa.String(length=64), nullable=False),
        sa.Column("commit_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("file_content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifact.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "requirement_version",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("commit_id", sa.String(length=64), nullable=False),
        sa.Column("commit_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("filepath_globs", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirement.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "implements",
        sa.Column("requirement_version_id", sa.Integer(), nullable=False),
        sa.Column("artifact_version_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artifact_version_id"],
            ["artifact_version.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_version_id"],
            ["requirement_version.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("requirement_version_id", "artifact_version_id"),
    )


def downgrade() -> None:
    op.drop_table("implements")
    op.drop_table("requirement_version")
    op.drop_table("artifact_version")
    op.drop_table("artifact")
    op.drop_table("requirement")
    op.drop_table("spec_version")
    op.drop_table("spec")
    op.drop_table("git_repo")
