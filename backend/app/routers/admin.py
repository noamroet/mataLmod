"""
Admin endpoints — requires X-Admin-Key header matching settings.ADMIN_API_KEY.

GET /api/v1/admin/scraper-status
  Returns the most recent ScrapeRun for every institution,
  plus a summary count by status.

POST /api/v1/admin/scraper-trigger/{institution_id}
  Enqueues an on-demand scrape run via Celery.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.institution import Institution
from app.models.scrape_run import ScrapeRun

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# ── Auth ──────────────────────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def _require_admin(key: str | None = Security(_api_key_header)) -> None:
    if not key or key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing admin API key.")


# ── Schemas ───────────────────────────────────────────────────────────────────


class ScrapeRunSummary(BaseModel):
    institution_id:   str
    institution_name: str
    last_run_id:      str | None
    last_started_at:  datetime | None
    last_completed_at: datetime | None
    last_status:      str | None
    last_records_updated: int | None
    anomaly_flag:     bool
    error_preview:    str | None


class ScraperStatusResponse(BaseModel):
    institutions:     list[ScrapeRunSummary]
    total_runs_today: int
    status_counts:    dict[str, int]


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.get(
    "/scraper-status",
    response_model=ScraperStatusResponse,
    summary="Latest scraper status per institution",
    dependencies=[Depends(_require_admin)],
)
async def scraper_status(
    db: AsyncSession = Depends(get_db),
) -> ScraperStatusResponse:
    """
    Returns the most recent ScrapeRun for every known institution,
    plus aggregate counts for the current UTC day.
    """
    # ── Fetch all institutions ────────────────────────────────────────────────
    inst_result = await db.execute(
        select(Institution).order_by(Institution.id)
    )
    institutions: list[Institution] = list(inst_result.scalars().all())

    # ── Latest run per institution (one query via correlated subquery) ────────
    # SELECT DISTINCT ON (institution_id) * FROM scrape_runs
    # ORDER BY institution_id, started_at DESC
    latest_stmt = (
        select(ScrapeRun)
        .distinct(ScrapeRun.institution_id)
        .order_by(ScrapeRun.institution_id, ScrapeRun.started_at.desc())
    )
    latest_result = await db.execute(latest_stmt)
    latest_runs: dict[str, ScrapeRun] = {
        r.institution_id: r for r in latest_result.scalars().all()
    }

    # ── Today's run counts ────────────────────────────────────────────────────
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_stmt = (
        select(ScrapeRun.status, func.count().label("cnt"))
        .where(ScrapeRun.started_at >= today_start)
        .group_by(ScrapeRun.status)
    )
    today_result = await db.execute(today_stmt)
    status_counts: dict[str, int] = {
        str(row.status.value if hasattr(row.status, "value") else row.status): row.cnt
        for row in today_result
    }
    total_runs_today = sum(status_counts.values())

    # ── Build response ────────────────────────────────────────────────────────
    summaries: list[ScrapeRunSummary] = []
    for inst in institutions:
        run = latest_runs.get(inst.id)
        summaries.append(
            ScrapeRunSummary(
                institution_id=inst.id,
                institution_name=inst.name_he,
                last_run_id=str(run.id) if run else None,
                last_started_at=run.started_at if run else None,
                last_completed_at=run.completed_at if run else None,
                last_status=str(run.status.value if hasattr(run.status, "value") else run.status) if run else None,
                last_records_updated=run.records_updated if run else None,
                anomaly_flag=run.anomaly_flag if run else False,
                error_preview=run.error_log[:200] if run and run.error_log else None,
            )
        )

    log.info("admin.scraper_status_requested", institution_count=len(summaries))
    return ScraperStatusResponse(
        institutions=summaries,
        total_runs_today=total_runs_today,
        status_counts=status_counts,
    )


@router.post(
    "/scraper-trigger/{institution_id}",
    summary="Trigger on-demand scrape for one institution",
    dependencies=[Depends(_require_admin)],
    status_code=202,
)
async def trigger_scrape(institution_id: str) -> dict[str, str]:
    """
    Enqueue an immediate scrape run for the given institution_id.
    Requires Celery worker to be running.
    """
    from celery import Celery  # lazy import — Celery not needed unless triggered

    celery_app = Celery(broker=settings.REDIS_URL)
    celery_app.send_task(
        "scraper.tasks.scrape_dispatch.scrape_institution",
        args=[institution_id],
        queue="scrapers",
    )
    log.info("admin.scrape_triggered", institution_id=institution_id)
    return {"status": "queued", "institution_id": institution_id}
