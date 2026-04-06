"""add programs.field index and roadmap_progress table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-05 00:00:00.000000

Changes:
  1. Add ix_programs_field index — speeds up field-filtered program queries
     (used heavily in results page filtering and advisor context builder)
  2. Create roadmap_progress table — stores per-user to-do item check states
     (synced from localStorage on login)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. programs.field index ───────────────────────────────────────────────
    # Used by: eligibility calculator (field filter), results page, advisor context
    op.create_index("ix_programs_field", "programs", ["field"])

    # ── 2. roadmap_progress table ─────────────────────────────────────────────
    # Stores user roadmap item completion state.
    # Unique on (user_id, program_id, item_index) — one row per check-box.
    op.create_table(
        "roadmap_progress",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "program_id",
            sa.UUID(),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column(
            "checked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "user_id",
            "program_id",
            "item_index",
            name="uq_roadmap_progress_user_program_item",
        ),
    )
    op.create_index("ix_roadmap_progress_user_id",    "roadmap_progress", ["user_id"])
    op.create_index("ix_roadmap_progress_program_id", "roadmap_progress", ["program_id"])


def downgrade() -> None:
    op.drop_table("roadmap_progress")
    op.drop_index("ix_programs_field", table_name="programs")
