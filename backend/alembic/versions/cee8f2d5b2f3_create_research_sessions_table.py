"""create research_sessions table

Revision ID: cee8f2d5b2f3
Revises:
Create Date: 2026-07-28 11:57:18.199478

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "cee8f2d5b2f3"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

research_session_status = postgresql.ENUM(
    "PENDING",
    "PLANNING",
    "RESEARCHING",
    "REPORT_GENERATION",
    "COMPLETED",
    "FAILED",
    name="research_session_status",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    research_session_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "research_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "status",
            research_session_status,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("research_sessions")
    research_session_status.drop(op.get_bind(), checkfirst=True)
