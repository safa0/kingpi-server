"""create package_events table

Revision ID: 96ea6a0b321c
Revises:
Create Date: 2026-03-06 03:06:05.702606

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "96ea6a0b321c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the package_events aggregate table.

    This table stores one row per (package, event_type) pair with a running
    counter and latest timestamp. The unique constraint enables PostgreSQL's
    INSERT ... ON CONFLICT DO UPDATE (upsert) for atomic counter increments.
    """
    op.create_table(
        "package_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("package", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_timestamp", sa.DateTime, nullable=True),
        sa.UniqueConstraint("package", "event_type", name="uq_package_event_type"),
    )


def downgrade() -> None:
    """Drop the package_events table."""
    op.drop_table("package_events")
