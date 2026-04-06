"""
POST /api/v1/eligibility/calculate

1. Load all active sekem_formulas (latest year per program) from DB,
   applying optional field / location / degree_type / institution filters.
2. Run rank_programs() from the sekem service.
3. Return the top 50 ranked results with full program metadata joined.
"""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.institution import Institution
from app.models.program import Program
from app.models.sekem_formula import SekemFormula as SekemFormulaModel
from app.schemas.eligibility import (
    EligibilityRequest,
    EligibilityResponse,
    EligibilityResultItem,
    ProfileSummary,
)
from app.schemas.institutions import InstitutionResponse
from app.schemas.programs import ProgramListItem
from app.schemas.sekem import BagrutRequirement, SekemFormula, SubjectBonus, UserProfile
from app.services.sekem import rank_programs, weighted_bagrut_average

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/eligibility",
    tags=["eligibility"],
)

_TOP_N = 50


@router.post(
    "/calculate",
    response_model=EligibilityResponse,
    summary="Calculate eligibility across all programs",
    description=(
        "Given a user's bagrut grades, psychometric score, and optional preferences, "
        "returns up to 50 programs ranked by eligibility and margin. "
        "Eligible programs appear first (highest margin first), then borderline, "
        "then ineligible. "
        "Always query `sekem_formulas.threshold_sekem` via the official university "
        "website before acting on these results — בדוק תמיד באתר הרשמי."
    ),
)
async def calculate_eligibility(
    request: EligibilityRequest,
    db: AsyncSession = Depends(get_db),
) -> EligibilityResponse:
    prefs = request.preferences

    # ── 1. Load latest sekem_formula per program (with program + institution) ─
    #
    # Subquery: (program_id, max_year) — the most recent formula per program
    latest_year_sq = (
        select(
            SekemFormulaModel.program_id,
            func.max(SekemFormulaModel.year).label("max_year"),
        )
        .group_by(SekemFormulaModel.program_id)
        .subquery()
    )

    stmt = (
        select(SekemFormulaModel, Program, Institution)
        .join(
            latest_year_sq,
            and_(
                SekemFormulaModel.program_id == latest_year_sq.c.program_id,
                SekemFormulaModel.year == latest_year_sq.c.max_year,
            ),
        )
        .join(Program, SekemFormulaModel.program_id == Program.id)
        .join(Institution, Program.institution_id == Institution.id)
        .where(Program.is_active == True)  # noqa: E712
    )

    # ── 2. Apply preference filters ───────────────────────────────────────────
    if prefs.fields:
        stmt = stmt.where(Program.field.in_(prefs.fields))
    if prefs.locations:
        stmt = stmt.where(Program.location.in_(prefs.locations))
    if prefs.degree_types:
        stmt = stmt.where(Program.degree_type.in_(prefs.degree_types))
    if prefs.institution_ids:
        stmt = stmt.where(Program.institution_id.in_(prefs.institution_ids))

    result = await db.execute(stmt)
    rows: list[tuple[SekemFormulaModel, Program, Institution]] = result.all()

    log.info("eligibility.formulas_loaded", count=len(rows))

    # ── 3. Convert ORM formulas → calculation schemas ─────────────────────────
    sekem_formulas: list[SekemFormula] = []
    programs_map: dict = {}  # program_id → (Program ORM, Institution ORM)

    for orm_formula, orm_program, orm_institution in rows:
        sekem_formulas.append(
            SekemFormula(
                program_id=orm_formula.program_id,
                bagrut_weight=orm_formula.bagrut_weight,
                psychometric_weight=orm_formula.psychometric_weight,
                threshold_sekem=orm_formula.threshold_sekem,
                subject_bonuses=[
                    SubjectBonus(**b) for b in (orm_formula.subject_bonuses or [])
                ],
                bagrut_requirements=[
                    BagrutRequirement(**r)
                    for r in (orm_formula.bagrut_requirements or [])
                ],
            )
        )
        programs_map[orm_formula.program_id] = (orm_program, orm_institution)

    # ── 4. Run sekem engine ───────────────────────────────────────────────────
    profile = UserProfile(
        bagrut_grades=request.bagrut_grades,
        psychometric=request.psychometric,
    )
    ranked = rank_programs(profile, sekem_formulas)

    # ── 5. Build top-N result items ───────────────────────────────────────────
    results: list[EligibilityResultItem] = []
    for rp in ranked[:_TOP_N]:
        orm_program, orm_institution = programs_map[rp.program_id]
        institution_resp = InstitutionResponse.model_validate(orm_institution)

        program_item = ProgramListItem(
            id=orm_program.id,
            institution_id=orm_program.institution_id,
            name_he=orm_program.name_he,
            name_en=orm_program.name_en,
            field=orm_program.field,
            degree_type=orm_program.degree_type,
            duration_years=orm_program.duration_years,
            location=orm_program.location,
            tuition_annual_ils=orm_program.tuition_annual_ils,
            official_url=orm_program.official_url,
            is_active=orm_program.is_active,
            created_at=orm_program.created_at,
            updated_at=orm_program.updated_at,
            institution=institution_resp,
        )
        results.append(
            EligibilityResultItem(
                rank=rp.rank,
                program=program_item,
                sekem=rp.sekem_result.sekem,
                threshold=rp.sekem_result.threshold,
                margin=rp.sekem_result.margin,
                eligible=rp.sekem_result.eligible,
                borderline=rp.sekem_result.borderline,
            )
        )

    # ── 6. Profile summary ────────────────────────────────────────────────────
    bagrut_avg = weighted_bagrut_average(profile.bagrut_grades)
    has_five_unit_math = any(
        g.subject_code == "math" and g.units == 5 for g in profile.bagrut_grades
    )
    profile_summary = ProfileSummary(
        bagrut_average=round(bagrut_avg, 2),
        psychometric=profile.psychometric,
        subject_count=len(profile.bagrut_grades),
        has_five_unit_math=has_five_unit_math,
    )

    log.info(
        "eligibility.calculated",
        total_matched=len(ranked),
        returned=len(results),
    )
    return EligibilityResponse(
        results=results,
        total=len(ranked),
        profile_summary=profile_summary,
    )
