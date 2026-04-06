"""
GET /api/v1/programs          — paginated program list with optional filters
GET /api/v1/programs/{id}     — full program detail with formula, syllabus,
                                career data, and data-freshness indicator

List responses are cached in Redis; detail responses are not (per-program
freshness is shown instead).
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core import cache
from app.core.database import get_db
from app.core.enums import ScrapeStatus
from app.models.institution import Institution
from app.models.program import Program
from app.models.scrape_run import ScrapeRun
from app.schemas.institutions import InstitutionResponse
from app.schemas.programs import (
    CareerDataResponse,
    DataFreshness,
    PaginatedPrograms,
    ProgramDetail,
    ProgramListItem,
    SekemFormulaResponse,
    SyllabusResponse,
)

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/programs",
    tags=["programs"],
)

_LIST_CACHE_PREFIX = "programs:list"


def _list_cache_key(
    field: str | None,
    institution_id: str | None,
    location: str | None,
    degree_type: str | None,
    page: int,
    limit: int,
) -> str:
    return (
        f"{_LIST_CACHE_PREFIX}:"
        f"f={field}:i={institution_id}:l={location}:d={degree_type}:"
        f"p={page}:lim={limit}"
    )


# ── List ──────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaginatedPrograms,
    summary="List programs with optional filters",
    description=(
        "Returns a paginated list of active programs. "
        "All filter parameters are optional and combinable. "
        "Results are cached for 1 hour per unique filter+page combination."
    ),
)
async def list_programs(
    field: str | None = Query(default=None, description="Field code, e.g. 'computer_science'"),
    institution_id: str | None = Query(default=None, description="Institution ID, e.g. 'TAU'"),
    location: str | None = Query(default=None, description="Location filter (Hebrew city name)"),
    degree_type: str | None = Query(default=None, description="Degree type: BA/BSc/BEd/BArch/BFA/LLB"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedPrograms:
    # ── Cache hit ─────────────────────────────────────────────────────────────
    ck = _list_cache_key(field, institution_id, location, degree_type, page, limit)
    cached = await cache.cache_get(ck)
    if cached is not None:
        log.debug("programs.list.cache_hit", key=ck)
        return PaginatedPrograms.model_validate(cached)

    # ── Build filtered base query ─────────────────────────────────────────────
    base = select(Program).where(Program.is_active == True)  # noqa: E712
    if field:
        base = base.where(Program.field == field)
    if institution_id:
        base = base.where(Program.institution_id == institution_id)
    if location:
        base = base.where(Program.location == location)
    if degree_type:
        base = base.where(Program.degree_type == degree_type)

    # ── Count ─────────────────────────────────────────────────────────────────
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total: int = count_result.scalar_one()

    # ── Paginate with institution eager-loaded ────────────────────────────────
    offset = (page - 1) * limit
    page_stmt = (
        base
        .options(joinedload(Program.institution))
        .order_by(Program.name_he)
        .offset(offset)
        .limit(limit)
    )
    page_result = await db.execute(page_stmt)
    programs = page_result.scalars().unique().all()

    items = [ProgramListItem.model_validate(p) for p in programs]
    pages = (total + limit - 1) // limit if total else 0

    response = PaginatedPrograms(items=items, total=total, page=page, limit=limit, pages=pages)

    await cache.cache_set(ck, response.model_dump(mode="json"), ttl=cache.PROGRAMS_TTL)
    log.info("programs.list.fetched", total=total, page=page)
    return response


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get(
    "/{program_id}",
    response_model=ProgramDetail,
    summary="Get full program detail",
    description=(
        "Returns complete program metadata including the latest admission formula, "
        "syllabus summary, career outcomes, and data-freshness indicator. "
        "Not cached — call when the user opens a program page."
    ),
)
async def get_program(
    program_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProgramDetail:
    # ── Load program with all eagerly-loaded associations ─────────────────────
    stmt = (
        select(Program)
        .options(
            joinedload(Program.institution),
            selectinload(Program.sekem_formulas),
            selectinload(Program.syllabi),
            selectinload(Program.career_data),
        )
        .where(Program.id == program_id)
    )
    result = await db.execute(stmt)
    program = result.scalar_one_or_none()

    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")

    # ── Pick latest record from each one-to-many collection ───────────────────
    latest_formula = max(
        program.sekem_formulas, key=lambda f: f.year, default=None
    )
    latest_syllabus = max(
        program.syllabi, key=lambda s: s.scraped_at, default=None
    )
    latest_career = max(
        program.career_data, key=lambda c: c.updated_at, default=None
    )

    # ── Last successful scrape run for this institution ───────────────────────
    scrape_stmt = (
        select(ScrapeRun)
        .where(
            ScrapeRun.institution_id == program.institution_id,
            ScrapeRun.status == ScrapeStatus.success,
        )
        .order_by(ScrapeRun.completed_at.desc())
        .limit(1)
    )
    scrape_result = await db.execute(scrape_stmt)
    last_scrape = scrape_result.scalar_one_or_none()

    # ── Build response ────────────────────────────────────────────────────────
    return ProgramDetail(
        id=program.id,
        institution_id=program.institution_id,
        name_he=program.name_he,
        name_en=program.name_en,
        field=program.field,
        degree_type=program.degree_type,
        duration_years=program.duration_years,
        location=program.location,
        tuition_annual_ils=program.tuition_annual_ils,
        official_url=program.official_url,
        is_active=program.is_active,
        created_at=program.created_at,
        updated_at=program.updated_at,
        institution=InstitutionResponse.model_validate(program.institution),
        latest_sekem_formula=(
            SekemFormulaResponse.model_validate(latest_formula)
            if latest_formula else None
        ),
        syllabus=(
            SyllabusResponse.model_validate(latest_syllabus)
            if latest_syllabus else None
        ),
        career_data=(
            CareerDataResponse.model_validate(latest_career)
            if latest_career else None
        ),
        data_freshness=DataFreshness(
            institution_id=program.institution_id,
            last_scrape_success=(
                last_scrape.completed_at if last_scrape else None
            ),
        ),
    )
