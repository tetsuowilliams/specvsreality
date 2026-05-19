"""Greenfield temporal schema.

Replaces all prior schema (git_repo / artifact / artifact_version / implements / spec /
spec_version / requirement / requirement_version) with a content-addressed, append-only
model that mirrors git history.

Existing databases are NOT upgradeable from the legacy schema; drop and recreate.

Revision ID: 0001
Revises:
Create Date: 2026-05-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("default_branch", sa.Text(), nullable=False, server_default="main"),
        sa.Column("clone_location", sa.Text(), nullable=True),
        sa.Column("cursor_position", sa.CHAR(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "blobs",
        sa.Column("sha", sa.CHAR(length=40), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("storage_url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("sha"),
    )

    op.create_table(
        "commits",
        sa.Column("sha", sa.CHAR(length=40), nullable=False),
        sa.Column("repository_id", sa.BigInteger(), nullable=False),
        sa.Column("author_name", sa.Text(), nullable=True),
        sa.Column("author_email", sa.Text(), nullable=True),
        sa.Column("author_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committer_name", sa.Text(), nullable=True),
        sa.Column("committer_email", sa.Text(), nullable=True),
        sa.Column("commit_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["repository_id"], ["repositories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("sha"),
    )
    op.create_index(
        "idx_commits_repo_date", "commits", ["repository_id", "commit_date"]
    )

    op.create_table(
        "commit_parents",
        sa.Column("commit_sha", sa.CHAR(length=40), nullable=False),
        sa.Column("parent_sha", sa.CHAR(length=40), nullable=False),
        sa.Column("parent_order", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(["commit_sha"], ["commits.sha"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_sha"], ["commits.sha"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("commit_sha", "parent_sha"),
    )
    op.create_index(
        "idx_commit_parents_parent", "commit_parents", ["parent_sha"]
    )

    op.create_table(
        "commit_files",
        sa.Column("commit_sha", sa.CHAR(length=40), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("blob_sha", sa.CHAR(length=40), nullable=False),
        sa.Column("mode", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["commit_sha"], ["commits.sha"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blob_sha"], ["blobs.sha"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("commit_sha", "path"),
    )
    op.create_index("idx_commit_files_blob", "commit_files", ["blob_sha"])

    op.create_table(
        "refs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("ref_type", sa.Text(), nullable=False),
        sa.Column("target_sha", sa.CHAR(length=40), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"], ["repositories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "name", name="uq_refs_repo_name"),
    )

    op.create_table(
        "specs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("spec_path", sa.Text(), nullable=False),
        sa.Column("plan_path", sa.Text(), nullable=False),
        sa.Column("tasks_path", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"], ["repositories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "name", name="uq_specs_repo_name"),
    )

    op.create_table(
        "spec_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("spec_id", sa.BigInteger(), nullable=False),
        sa.Column("spec_blob_sha", sa.CHAR(length=40), nullable=False),
        sa.Column("plan_blob_sha", sa.CHAR(length=40), nullable=True),
        sa.Column("tasks_blob_sha", sa.CHAR(length=40), nullable=True),
        sa.Column("first_seen_commit", sa.CHAR(length=40), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["spec_id"], ["specs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["spec_blob_sha"], ["blobs.sha"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["plan_blob_sha"], ["blobs.sha"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["tasks_blob_sha"], ["blobs.sha"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["first_seen_commit"], ["commits.sha"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "spec_id",
            "spec_blob_sha",
            "plan_blob_sha",
            "tasks_blob_sha",
            name="uq_spec_versions_triplet",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index("idx_spec_versions_spec", "spec_versions", ["spec_id"])

    op.create_table(
        "requirements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("spec_id", sa.BigInteger(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["spec_id"], ["specs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "spec_id", "external_id", name="uq_requirements_spec_external_id"
        ),
    )

    op.create_table(
        "requirement_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("requirement_id", sa.BigInteger(), nullable=False),
        sa.Column("spec_version_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.CHAR(length=40), nullable=False),
        sa.Column("extraction_model", sa.Text(), nullable=False),
        sa.Column("extraction_prompt", sa.Text(), nullable=False),
        sa.Column(
            "path_globs",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"], ["requirements.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["spec_version_id"], ["spec_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requirement_id",
            "spec_version_id",
            name="uq_requirement_versions_req_specver",
        ),
    )
    op.create_index(
        "idx_reqver_specver", "requirement_versions", ["spec_version_id"]
    )

    op.create_table(
        "implementation_claims",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("requirement_version_id", sa.BigInteger(), nullable=False),
        sa.Column("blob_sha", sa.CHAR(length=40), nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["requirement_version_id"],
            ["requirement_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["blob_sha"], ["blobs.sha"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_claims_lookup",
        "implementation_claims",
        ["requirement_version_id", "blob_sha", sa.text("evaluated_at DESC")],
    )
    op.create_index(
        "idx_claims_blob", "implementation_claims", ["blob_sha"]
    )

    op.execute(
        """
        CREATE VIEW current_claims AS
        SELECT DISTINCT ON (requirement_version_id, blob_sha) *
        FROM implementation_claims
        ORDER BY requirement_version_id, blob_sha, evaluated_at DESC
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS current_claims")
    op.drop_index("idx_claims_blob", table_name="implementation_claims")
    op.drop_index("idx_claims_lookup", table_name="implementation_claims")
    op.drop_table("implementation_claims")
    op.drop_index("idx_reqver_specver", table_name="requirement_versions")
    op.drop_table("requirement_versions")
    op.drop_table("requirements")
    op.drop_index("idx_spec_versions_spec", table_name="spec_versions")
    op.drop_table("spec_versions")
    op.drop_table("specs")
    op.drop_table("refs")
    op.drop_index("idx_commit_files_blob", table_name="commit_files")
    op.drop_table("commit_files")
    op.drop_index("idx_commit_parents_parent", table_name="commit_parents")
    op.drop_table("commit_parents")
    op.drop_index("idx_commits_repo_date", table_name="commits")
    op.drop_table("commits")
    op.drop_table("blobs")
    op.drop_table("repositories")
