"""unique spec identity per repo folder and spec version per commit

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-08 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Remove duplicate specs created by concurrent scans (keep lowest id).
    op.execute(
        sa.text(
            """
            DELETE FROM spec AS newer
            USING spec AS older
            WHERE newer.repo_id = older.repo_id
              AND newer.paper_id = older.paper_id
              AND newer.id > older.id
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM spec_version AS newer
            USING spec_version AS older
            WHERE newer.spec_id = older.spec_id
              AND newer.commit_id = older.commit_id
              AND newer.id > older.id
            """
        )
    )

    op.create_unique_constraint(
        "uq_spec_repo_paper_id",
        "spec",
        ["repo_id", "paper_id"],
    )
    op.create_unique_constraint(
        "uq_spec_version_spec_commit",
        "spec_version",
        ["spec_id", "commit_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_spec_version_spec_commit", "spec_version", type_="unique")
    op.drop_constraint("uq_spec_repo_paper_id", "spec", type_="unique")
