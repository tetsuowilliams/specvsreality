"""implementation_at_commit table; implements links via evaluation rows

Revision ID: 20260522_0001
Revises: 20260521_0002
Create Date: 2026-05-22 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260522_0001"
down_revision: Union[str, Sequence[str], None] = "20260521_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "implementation_at_commit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evaluation_commit_sha", sa.String(length=64), nullable=False),
        sa.Column("requirement_version_id", sa.Integer(), nullable=False),
        sa.Column("implemented", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("gaps", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(
            ["requirement_version_id"],
            ["requirement_version.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requirement_version_id",
            "evaluation_commit_sha",
            name="uq_implementation_at_commit_rv_commit",
        ),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO implementation_at_commit (
                evaluation_commit_sha,
                requirement_version_id,
                implemented,
                summary,
                gaps
            )
            SELECT
                rv.commit_sha,
                rv.id,
                COALESCE(rv.implemented, FALSE),
                rv.summary,
                rv.gaps
            FROM requirement_version rv
            WHERE rv.implemented IS NOT NULL
               OR rv.summary IS NOT NULL
               OR rv.gaps IS NOT NULL
            """
        )
    )

    op.add_column(
        "implements",
        sa.Column("implementation_at_commit_id", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE implements AS i
            SET implementation_at_commit_id = iac.id
            FROM implementation_at_commit AS iac
            WHERE iac.requirement_version_id = i.requirement_version_id
              AND iac.evaluation_commit_sha = (
                  SELECT rv.commit_sha
                  FROM requirement_version rv
                  WHERE rv.id = i.requirement_version_id
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO implementation_at_commit (
                evaluation_commit_sha,
                requirement_version_id,
                implemented,
                summary,
                gaps
            )
            SELECT rv.commit_sha, rv.id, FALSE, NULL, NULL
            FROM implements AS i
            JOIN requirement_version AS rv ON rv.id = i.requirement_version_id
            WHERE i.implementation_at_commit_id IS NULL
            ON CONFLICT (requirement_version_id, evaluation_commit_sha) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE implements AS i
            SET implementation_at_commit_id = iac.id
            FROM implementation_at_commit AS iac
            WHERE iac.requirement_version_id = i.requirement_version_id
              AND iac.evaluation_commit_sha = (
                  SELECT rv.commit_sha
                  FROM requirement_version rv
                  WHERE rv.id = i.requirement_version_id
              )
              AND i.implementation_at_commit_id IS NULL
            """
        )
    )

    op.drop_constraint("implements_pkey", "implements", type_="primary")
    op.drop_constraint(
        "implements_requirement_version_id_fkey",
        "implements",
        type_="foreignkey",
    )
    op.drop_column("implements", "requirement_version_id")
    op.alter_column(
        "implements",
        "implementation_at_commit_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "implements_implementation_at_commit_id_fkey",
        "implements",
        "implementation_at_commit",
        ["implementation_at_commit_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_primary_key(
        "implements_pkey",
        "implements",
        ["implementation_at_commit_id", "artifact_version_id"],
    )

    op.drop_column("requirement_version", "gaps")
    op.drop_column("requirement_version", "summary")
    op.drop_column("requirement_version", "implemented")


def downgrade() -> None:
    op.add_column("requirement_version", sa.Column("implemented", sa.Boolean(), nullable=True))
    op.add_column("requirement_version", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "requirement_version",
        sa.Column("gaps", postgresql.ARRAY(sa.String()), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE requirement_version AS rv
            SET implemented = iac.implemented,
                summary = iac.summary,
                gaps = iac.gaps
            FROM implementation_at_commit AS iac
            WHERE iac.requirement_version_id = rv.id
              AND iac.evaluation_commit_sha = rv.commit_sha
            """
        )
    )

    op.add_column(
        "implements",
        sa.Column("requirement_version_id", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE implements AS i
            SET requirement_version_id = iac.requirement_version_id
            FROM implementation_at_commit AS iac
            WHERE iac.id = i.implementation_at_commit_id
            """
        )
    )

    op.drop_constraint("implements_pkey", "implements", type_="primary")
    op.drop_constraint(
        "implements_implementation_at_commit_id_fkey",
        "implements",
        type_="foreignkey",
    )
    op.drop_column("implements", "implementation_at_commit_id")
    op.alter_column(
        "implements",
        "requirement_version_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "implements_requirement_version_id_fkey",
        "implements",
        "requirement_version",
        ["requirement_version_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_primary_key(
        "implements_pkey",
        "implements",
        ["requirement_version_id", "artifact_version_id"],
    )

    op.drop_table("implementation_at_commit")
