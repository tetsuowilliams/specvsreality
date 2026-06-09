"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-08 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SPEC_ITEM_TYPE_VALUES = (
    "functional_behavior",
    "input_rule",
    "output_rule",
    "error_handling",
    "edge_case",
    "exclusion",
    "non_functional_constraint",
    "acceptance_scenario",
    "context",
    "task",
    "design_note",
)

SPEC_ITEM_IMPORTANCE_VALUES = (
    "must",
    "should",
    "optional",
    "context",
)


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
        "commit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("commit_message", sa.Text(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["git_repo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repo_id", "commit_sha", name="uq_commit_repo_sha"),
    )
    op.create_index(op.f("ix_commit_repo_id"), "commit", ["repo_id"], unique=False)

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
        sa.Column("commit_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("spec_md", sa.Text(), nullable=False),
        sa.Column("tasks_md", sa.Text(), nullable=True),
        sa.Column("plan_md", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["spec_id"], ["spec.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["commit_id"], ["commit.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_spec_version_commit_id"), "spec_version", ["commit_id"], unique=False)

    spec_item_type = postgresql.ENUM(*SPEC_ITEM_TYPE_VALUES, name="spec_item_type")
    spec_item_importance = postgresql.ENUM(*SPEC_ITEM_IMPORTANCE_VALUES, name="spec_item_importance")

    op.create_table(
        "spec_item",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spec_version_id", sa.Integer(), nullable=False),
        sa.Column("local_key", sa.String(), nullable=False),
        sa.Column("item_type", spec_item_type, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_quote", sa.Text(), nullable=False),
        sa.Column("importance", spec_item_importance, nullable=False),
        sa.Column("success_criteria", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("failure_criteria", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("highlight_spans", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["spec_version_id"], ["spec_version.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_spec_item_spec_version_id"), "spec_item", ["spec_version_id"], unique=False)

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
        sa.Column("commit_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("file_content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifact.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["commit_id"], ["commit.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_artifact_version_commit_id"), "artifact_version", ["commit_id"], unique=False)

    op.create_table(
        "artifact_candidate",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spec_version_id", sa.Integer(), nullable=False),
        sa.Column("artifact_version_id", sa.Integer(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["spec_version_id"], ["spec_version.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artifact_version_id"], ["artifact_version.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_artifact_candidate_spec_version_id"),
        "artifact_candidate",
        ["spec_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_artifact_candidate_artifact_version_id"),
        "artifact_candidate",
        ["artifact_version_id"],
        unique=False,
    )

    op.create_table(
        "implementation_at_commit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spec_item_id", sa.Integer(), nullable=False),
        sa.Column("commit_id", sa.Integer(), nullable=False),
        sa.Column("implemented", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("gaps", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["spec_item_id"], ["spec_item.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["commit_id"], ["commit.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "spec_item_id",
            "commit_id",
            name="uq_implementation_at_commit_item_commit",
        ),
    )
    op.create_index(
        op.f("ix_implementation_at_commit_spec_item_id"),
        "implementation_at_commit",
        ["spec_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_implementation_at_commit_commit_id"),
        "implementation_at_commit",
        ["commit_id"],
        unique=False,
    )

    op.create_table(
        "implements",
        sa.Column("implementation_at_commit_id", sa.Integer(), nullable=False),
        sa.Column("artifact_version_id", sa.Integer(), nullable=False),
        sa.Column("evidence_file", sa.Text(), nullable=True),
        sa.Column("evidence_line_number", sa.Integer(), nullable=True),
        sa.Column("evidence_snippet", sa.Text(), nullable=True),
        sa.Column("evidence_relevance", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["implementation_at_commit_id"],
            ["implementation_at_commit.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_version_id"],
            ["artifact_version.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("implementation_at_commit_id", "artifact_version_id"),
    )

    op.create_table(
        "agent_run_metric",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("commit_id", sa.Integer(), nullable=False),
        sa.Column("agent", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("ran_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["commit_id"], ["commit.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repo_id"], ["git_repo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_run_metric_commit_id"),
        "agent_run_metric",
        ["commit_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_run_metric_repo_id"),
        "agent_run_metric",
        ["repo_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_run_metric_repo_id"), table_name="agent_run_metric")
    op.drop_index(op.f("ix_agent_run_metric_commit_id"), table_name="agent_run_metric")
    op.drop_table("agent_run_metric")
    op.drop_table("implements")
    op.drop_index(op.f("ix_implementation_at_commit_commit_id"), table_name="implementation_at_commit")
    op.drop_index(op.f("ix_implementation_at_commit_spec_item_id"), table_name="implementation_at_commit")
    op.drop_table("implementation_at_commit")
    op.drop_index(op.f("ix_artifact_candidate_artifact_version_id"), table_name="artifact_candidate")
    op.drop_index(op.f("ix_artifact_candidate_spec_version_id"), table_name="artifact_candidate")
    op.drop_table("artifact_candidate")
    op.drop_index(op.f("ix_artifact_version_commit_id"), table_name="artifact_version")
    op.drop_table("artifact_version")
    op.drop_table("artifact")
    op.drop_index(op.f("ix_spec_item_spec_version_id"), table_name="spec_item")
    op.drop_table("spec_item")
    op.drop_index(op.f("ix_spec_version_commit_id"), table_name="spec_version")
    op.drop_table("spec_version")
    op.drop_table("spec")
    op.drop_index(op.f("ix_commit_repo_id"), table_name="commit")
    op.drop_table("commit")
    op.drop_table("git_repo")

    op.execute("DROP TYPE IF EXISTS spec_item_importance")
    op.execute("DROP TYPE IF EXISTS spec_item_type")
