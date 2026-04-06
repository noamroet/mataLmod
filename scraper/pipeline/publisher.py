"""
Scrape → DB publisher.

Upsert rules
------------
programs      : natural key = (institution_id, name_he, degree_type)
                create on first encounter; update mutable fields on re-run
sekem_formulas: key = (program_id, year) — APPEND only, never delete
syllabi       : one row per program; replace raw_html + reset summarised fields

All writes happen inside one session; the caller commits after publish_results
returns, so an exception mid-way leaves the DB unchanged.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# These imports assume backend/ is on sys.path (set via PYTHONPATH in Docker
# or via pyproject.toml [tool.pytest.ini_options] pythonpath in tests).
from app.models.program import Program
from app.models.sekem_formula import SekemFormula
from app.models.syllabus import Syllabus
from scrapers.base import ScrapeResult

log = structlog.get_logger(__name__)


async def publish_results(
    db: AsyncSession,
    results: list[ScrapeResult],
) -> int:
    """
    Upsert all successful ScrapeResults into the live DB.

    Returns the number of programs inserted or updated.
    Does NOT commit — the caller (Celery task) commits after this returns.
    """
    records_updated = 0

    for result in results:
        if not result.scrape_ok:
            continue
        try:
            program = await _upsert_program(db, result)
            await _upsert_sekem_formula(db, program.id, result)
            if result.raw_html:
                await _upsert_syllabus(db, program.id, result)
            records_updated += 1
        except Exception as exc:
            log.error(
                "publisher.record_failed",
                name_he=result.name_he,
                error=str(exc),
            )
            # Continue — don't let one bad record abort the whole batch.

    log.info("publisher.done", records_updated=records_updated)
    return records_updated


# ── Private helpers ───────────────────────────────────────────────────────────

async def _upsert_program(db: AsyncSession, result: ScrapeResult) -> Program:
    stmt = select(Program).where(
        Program.institution_id == result.institution_id,
        Program.name_he == result.name_he,
        Program.degree_type == result.degree_type,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing is None:
        program = Program(
            id=uuid.uuid4(),
            institution_id=result.institution_id,
            name_he=result.name_he,
            name_en=result.name_en,
            field=result.field,
            degree_type=result.degree_type,
            duration_years=result.duration_years,
            location=result.location,
            tuition_annual_ils=result.tuition_annual_ils,
            official_url=result.official_url,
            is_active=True,
        )
        db.add(program)
        await db.flush()  # get auto-generated id before FK inserts
        log.info("publisher.program_inserted", name_he=result.name_he)
    else:
        existing.name_en = result.name_en
        existing.field = result.field
        existing.duration_years = result.duration_years
        existing.tuition_annual_ils = result.tuition_annual_ils
        existing.official_url = result.official_url
        existing.updated_at = datetime.now(timezone.utc)
        program = existing
        log.debug("publisher.program_updated", name_he=result.name_he)

    return program


async def _upsert_sekem_formula(
    db: AsyncSession, program_id: uuid.UUID, result: ScrapeResult
) -> SekemFormula:
    stmt = select(SekemFormula).where(
        SekemFormula.program_id == program_id,
        SekemFormula.year == result.sekem_year,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing is None:
        formula = SekemFormula(
            id=uuid.uuid4(),
            program_id=program_id,
            year=result.sekem_year,
            bagrut_weight=result.bagrut_weight,
            psychometric_weight=result.psychometric_weight,
            threshold_sekem=result.threshold_sekem,
            subject_bonuses=result.subject_bonuses,
            bagrut_requirements=result.bagrut_requirements,
            scraped_at=result.scraped_at,
            source_url=result.formula_source_url or result.official_url,
        )
        db.add(formula)
        log.info(
            "publisher.formula_inserted",
            name_he=result.name_he,
            year=result.sekem_year,
        )
    else:
        existing.bagrut_weight = result.bagrut_weight
        existing.psychometric_weight = result.psychometric_weight
        existing.threshold_sekem = result.threshold_sekem
        existing.subject_bonuses = result.subject_bonuses
        existing.bagrut_requirements = result.bagrut_requirements
        existing.scraped_at = result.scraped_at
        formula = existing
        log.debug(
            "publisher.formula_updated",
            name_he=result.name_he,
            year=result.sekem_year,
        )

    return formula


async def _upsert_syllabus(
    db: AsyncSession, program_id: uuid.UUID, result: ScrapeResult
) -> Syllabus:
    # Get the most recent syllabus for this program (if any)
    stmt = (
        select(Syllabus)
        .where(Syllabus.program_id == program_id)
        .order_by(Syllabus.scraped_at.desc())
        .limit(1)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing is None:
        syllabus = Syllabus(
            id=uuid.uuid4(),
            program_id=program_id,
            raw_html=result.raw_html,
            scraped_at=result.scraped_at,
            # AI-generated summary fields left null; filled by summarize Celery task
        )
        db.add(syllabus)
    else:
        existing.raw_html = result.raw_html
        existing.scraped_at = result.scraped_at
        # Reset summarisation so the AI task re-processes the updated content
        existing.summarized_at = None
        existing.year_1_summary_he = None
        existing.year_2_summary_he = None
        existing.year_3_summary_he = None
        syllabus = existing

    return syllabus
