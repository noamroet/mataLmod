"""
Celery tasks for the scraper pipeline.

Task: scrape_institution(institution_id)
  1. Create a ScrapeRun record (status=running)
  2. Instantiate the correct scraper from SCRAPER_REGISTRY
  3. Run scraper.scrape()
  4. Validate results; if anomaly → mark run as anomaly (no DB write)
  5. Publish to live DB; update ScrapeRun to success/failed

Beat schedule:
  scrape-tau-nightly  : TAU at 23:00 UTC (= 02:00 Israel IDT, UTC+3)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from celery.schedules import crontab
from sqlalchemy import select

# Import the Celery app so task registration works when this module is autodiscovered
from scraper.celery_app import app as celery_app
from scrapers.tau import TauScraper

# These imports require backend/ on sys.path — see pyproject.toml pythonpath
from app.core.database import AsyncSessionLocal
from app.core.enums import ScrapeStatus
from app.models.scrape_run import ScrapeRun
from pipeline.publisher import publish_results
from pipeline.validator import detect_anomaly

log = structlog.get_logger(__name__)

# ── Registry: institution_id → scraper class ──────────────────────────────────

SCRAPER_REGISTRY: dict[str, type] = {
    "TAU": TauScraper,
    # HUJI, TECHNION, BGU, BIU, HAIFA, ARIEL will be added here
}


# ── Async implementation ──────────────────────────────────────────────────────

async def _run_scrape(institution_id: str) -> dict:
    """Core async logic; wrapped by the Celery task below."""
    if institution_id not in SCRAPER_REGISTRY:
        raise ValueError(f"No scraper registered for institution: {institution_id!r}")

    async with AsyncSessionLocal() as db:
        # ── Create ScrapeRun record ───────────────────────────────────────────
        run = ScrapeRun(
            institution_id=institution_id,
            status=ScrapeStatus.running,
        )
        db.add(run)
        await db.flush()  # get run.id before continuing
        run_id = run.id
        log.info("scrape.started", institution=institution_id, run_id=str(run_id))

        try:
            # ── Scrape ────────────────────────────────────────────────────────
            scraper_cls = SCRAPER_REGISTRY[institution_id]
            async with scraper_cls() as scraper:
                results = await scraper.scrape()

            # ── Validate ──────────────────────────────────────────────────────
            anomaly = detect_anomaly(results, institution_id)
            if anomaly:
                run.status = ScrapeStatus.anomaly
                run.anomaly_flag = True
                run.completed_at = datetime.now(timezone.utc)
                await db.commit()
                log.warning("scrape.anomaly", institution=institution_id)
                return {
                    "status": ScrapeStatus.anomaly.value,
                    "records_updated": 0,
                    "run_id": str(run_id),
                }

            # ── Publish ───────────────────────────────────────────────────────
            records = await publish_results(db, results)
            run.status = ScrapeStatus.success
            run.records_updated = records
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

            log.info(
                "scrape.success",
                institution=institution_id,
                records=records,
                run_id=str(run_id),
            )
            return {
                "status": ScrapeStatus.success.value,
                "records_updated": records,
                "run_id": str(run_id),
            }

        except Exception as exc:
            log.exception("scrape.failed", institution=institution_id, error=str(exc))
            run.status = ScrapeStatus.failed
            run.error_log = str(exc)
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise


# ── Celery task ───────────────────────────────────────────────────────────────

@celery_app.task(
    name="scraper.tasks.scrape_dispatch.scrape_institution",
    bind=True,
    max_retries=0,  # scraper handles its own retries internally
    acks_late=True,
)
def scrape_institution(self, institution_id: str) -> dict:
    """
    Celery task: scrape one institution and publish results to the live DB.

    Called by Beat for nightly runs and by the admin panel for on-demand runs.
    """
    return asyncio.run(_run_scrape(institution_id))
