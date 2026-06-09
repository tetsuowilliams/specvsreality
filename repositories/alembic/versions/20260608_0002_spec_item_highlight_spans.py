"""add spec_item.highlight_spans

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-08 17:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # IF NOT EXISTS: fresh databases already have this column from 0001_initial.
    op.execute(
        sa.text(
            "ALTER TABLE spec_item "
            "ADD COLUMN IF NOT EXISTS highlight_spans JSONB"
        )
    )


def downgrade() -> None:
    op.drop_column("spec_item", "highlight_spans")
