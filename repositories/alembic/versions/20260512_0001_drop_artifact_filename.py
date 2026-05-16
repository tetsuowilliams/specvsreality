"""drop artifact.filename (legacy column)

Revision ID: 20260512_0001
Revises: 20250331_0001
Create Date: 2026-05-12 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260512_0001"
down_revision: Union[str, Sequence[str], None] = "20250331_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE artifact DROP COLUMN IF EXISTS filename"))


def downgrade() -> None:
    op.add_column(
        "artifact",
        sa.Column(
            "filename",
            sa.String(length=1024),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("artifact", "filename", server_default=None)
