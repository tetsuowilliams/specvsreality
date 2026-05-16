"""spec_version: nullable tasks_md and plan_md

Revision ID: 20260514_0001
Revises: 20260512_0001
Create Date: 2026-05-14 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260514_0001"
down_revision: Union[str, Sequence[str], None] = "20260512_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "spec_version",
        "tasks_md",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.alter_column(
        "spec_version",
        "plan_md",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(sa.text("UPDATE spec_version SET tasks_md = '' WHERE tasks_md IS NULL"))
    op.execute(sa.text("UPDATE spec_version SET plan_md = '' WHERE plan_md IS NULL"))
    op.alter_column(
        "spec_version",
        "tasks_md",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column(
        "spec_version",
        "plan_md",
        existing_type=sa.Text(),
        nullable=False,
    )
