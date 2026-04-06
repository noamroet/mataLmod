"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-05 00:00:00.000000

Creates all eight tables for MaTaLmod v1:
  institutions, programs, sekem_formulas, syllabi,
  career_data, scrape_runs, users, saved_programs

Also creates three PostgreSQL ENUM types:
  institution_type, demand_trend, scrape_status
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. PostgreSQL ENUM types ──────────────────────────────────────────────
    institution_type = postgresql.ENUM(
        "university", "college", name="institution_type", create_type=True
    )
    institution_type.create(op.get_bind(), checkfirst=True)

    demand_trend = postgresql.ENUM(
        "growing", "stable", "declining", name="demand_trend", create_type=True
    )
    demand_trend.create(op.get_bind(), checkfirst=True)

    scrape_status = postgresql.ENUM(
        "running", "success", "failed", "anomaly", name="scrape_status", create_type=True
    )
    scrape_status.create(op.get_bind(), checkfirst=True)

    # ── 2. institutions ───────────────────────────────────────────────────────
    op.create_table(
        "institutions",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("name_he", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "university", "college", name="institution_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("website_url", sa.String(500), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── 3. users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=True, unique=True),
        sa.Column("auth_provider", sa.String(50), nullable=False),
        sa.Column(
            "profile",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── 4. programs ───────────────────────────────────────────────────────────
    op.create_table(
        "programs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.String(20),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name_he", sa.String(300), nullable=False),
        sa.Column("name_en", sa.String(300), nullable=True),
        sa.Column("field", sa.String(50), nullable=False),
        sa.Column("degree_type", sa.String(20), nullable=False),
        sa.Column("duration_years", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("tuition_annual_ils", sa.Integer(), nullable=True),
        sa.Column("official_url", sa.String(500), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_programs_institution_id", "programs", ["institution_id"])

    # ── 5. sekem_formulas ─────────────────────────────────────────────────────
    op.create_table(
        "sekem_formulas",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "program_id",
            sa.UUID(),
            sa.ForeignKey("programs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("bagrut_weight", sa.Float(), nullable=False),
        sa.Column("psychometric_weight", sa.Float(), nullable=False),
        sa.Column("threshold_sekem", sa.Float(), nullable=False),
        sa.Column(
            "subject_bonuses",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "bagrut_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("source_url", sa.String(500), nullable=False),
    )
    op.create_index("ix_sekem_formulas_program_id", "sekem_formulas", ["program_id"])
    # Partial index: fast lookup of current-year formula per program
    op.create_index(
        "ix_sekem_formulas_program_year",
        "sekem_formulas",
        ["program_id", "year"],
    )

    # ── 6. syllabi ────────────────────────────────────────────────────────────
    op.create_table(
        "syllabi",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "program_id",
            sa.UUID(),
            sa.ForeignKey("programs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("year_1_summary_he", sa.Text(), nullable=True),
        sa.Column("year_2_summary_he", sa.Text(), nullable=True),
        sa.Column("year_3_summary_he", sa.Text(), nullable=True),
        sa.Column(
            "core_courses",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "elective_tracks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("one_line_pitch_he", sa.String(500), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=False),
        sa.Column("summarized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_syllabi_program_id", "syllabi", ["program_id"])

    # ── 7. career_data ────────────────────────────────────────────────────────
    op.create_table(
        "career_data",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "program_id",
            sa.UUID(),
            sa.ForeignKey("programs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "job_titles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("avg_salary_min_ils", sa.Integer(), nullable=True),
        sa.Column("avg_salary_max_ils", sa.Integer(), nullable=True),
        sa.Column(
            "demand_trend",
            postgresql.ENUM(
                "growing", "stable", "declining", name="demand_trend", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("data_year", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(300), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_career_data_program_id", "career_data", ["program_id"])

    # ── 8. scrape_runs ────────────────────────────────────────────────────────
    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.String(20),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "running", "success", "failed", "anomaly",
                name="scrape_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "records_updated",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "anomaly_flag",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("error_log", sa.Text(), nullable=True),
    )
    op.create_index("ix_scrape_runs_institution_id", "scrape_runs", ["institution_id"])

    # ── 9. saved_programs ─────────────────────────────────────────────────────
    op.create_table(
        "saved_programs",
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
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "user_id", "program_id", name="uq_saved_programs_user_program"
        ),
    )
    op.create_index("ix_saved_programs_user_id", "saved_programs", ["user_id"])
    op.create_index("ix_saved_programs_program_id", "saved_programs", ["program_id"])


def downgrade() -> None:
    # Drop tables in reverse FK dependency order
    op.drop_table("saved_programs")
    op.drop_table("scrape_runs")
    op.drop_table("career_data")
    op.drop_table("syllabi")
    op.drop_table("sekem_formulas")
    op.drop_table("programs")
    op.drop_table("users")
    op.drop_table("institutions")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS scrape_status")
    op.execute("DROP TYPE IF EXISTS demand_trend")
    op.execute("DROP TYPE IF EXISTS institution_type")
