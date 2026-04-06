"""
GET /api/v1/institutions — list all active institutions.

Results are cached in Redis for INSTITUTIONS_TTL seconds.
Cache is invalidated by app.core.cache.invalidate_institutions()
after each successful scraper run.
"""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache
from app.core.database import get_db
from app.models.institution import Institution
from app.schemas.institutions import InstitutionResponse

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/institutions",
    tags=["institutions"],
)

_CACHE_KEY = "institutions:all"


@router.get(
    "",
    response_model=list[InstitutionResponse],
    summary="List all active institutions",
    description=(
        "Returns all universities and colleges in the v1 scope. "
        "Response is cached for 1 hour."
    ),
)
async def list_institutions(
    db: AsyncSession = Depends(get_db),
) -> list[InstitutionResponse]:
    # ── Cache hit ─────────────────────────────────────────────────────────────
    cached = await cache.cache_get(_CACHE_KEY)
    if cached is not None:
        log.debug("institutions.cache_hit")
        return [InstitutionResponse.model_validate(item) for item in cached]

    # ── DB query ──────────────────────────────────────────────────────────────
    stmt = (
        select(Institution)
        .where(Institution.is_active == True)  # noqa: E712
        .order_by(Institution.name_en)
    )
    result = await db.execute(stmt)
    institutions = result.scalars().all()

    response = [InstitutionResponse.model_validate(inst) for inst in institutions]

    # ── Populate cache ────────────────────────────────────────────────────────
    await cache.cache_set(
        _CACHE_KEY,
        [r.model_dump(mode="json") for r in response],
        ttl=cache.INSTITUTIONS_TTL,
    )
    log.info("institutions.fetched", count=len(response))
    return response
