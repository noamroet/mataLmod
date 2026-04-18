"""
Celery task: AI syllabus summariser.

Fetches syllabi whose year_1_summary_he is NULL (i.e. not yet summarised),
sends raw HTML to Claude, and writes back plain-language Hebrew year summaries
plus a one-line pitch.

Runs nightly via Beat at 01:00 UTC (after the scrape tasks complete at 23:00 UTC).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import anthropic
import structlog
from sqlalchemy import select

from scraper.celery_app import app as celery_app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.syllabus import Syllabus

log = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_MODEL = "claude-haiku-4-5-20251001"   # fast + cheap for batch HTML summarisation
_BATCH_SIZE = 10                        # syllabi processed per task invocation
_MAX_HTML_CHARS = 30_000               # truncate very large raw_html before sending


_SYSTEM_PROMPT = """אתה עוזר אקדמי. קרא את תוכן הסילבוס של תוכנית לימודים ישראלית וסכם אותו בעברית.

כללים:
1. כתוב רק על בסיס הטקסט שסופק — אל תמציא.
2. כתוב בגוף שלישי, ממוקד, עד 3 משפטים לשנה.
3. אם אין מידע על שנה מסוימת — החזר null עבור אותו שדה.
4. one_line_pitch: משפט אחד שמסביר למה ללמוד את זה (עד 120 תווים).

החזר JSON בלבד (ללא הסבר), במבנה:
{
  "year_1": "<סיכום שנה א> או null",
  "year_2": "<סיכום שנה ב> או null",
  "year_3": "<סיכום שנה ג> או null",
  "one_line_pitch": "<משפט שיווקי> או null"
}"""


# ── Async core ────────────────────────────────────────────────────────────────


async def _summarise_syllabus(syllabus: Syllabus, client: anthropic.AsyncAnthropic) -> dict:
    """Call Claude to summarise one syllabus; return parsed JSON dict."""
    raw = (syllabus.raw_html or "")[:_MAX_HTML_CHARS]
    message = await client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw}],
    )

    import json
    text = message.content[0].text.strip()
    # Strip markdown code fences if model wraps the JSON
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


async def _run_batch() -> dict:
    """Fetch up to _BATCH_SIZE unsummarised syllabi and summarise them."""
    if not settings.ANTHROPIC_API_KEY:
        log.warning("summarize.no_api_key_skipping")
        return {"summarised": 0, "skipped": 0, "errors": 0}

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async with AsyncSessionLocal() as db:
        stmt = (
            select(Syllabus)
            .where(Syllabus.year_1_summary_he.is_(None))
            .order_by(Syllabus.scraped_at.desc())
            .limit(_BATCH_SIZE)
        )
        result = await db.execute(stmt)
        syllabi: list[Syllabus] = list(result.scalars().all())

        if not syllabi:
            log.info("summarize.nothing_to_do")
            return {"summarised": 0, "skipped": 0, "errors": 0}

        summarised = skipped = errors = 0

        for syl in syllabi:
            if not syl.raw_html:
                skipped += 1
                continue

            try:
                data = await _summarise_syllabus(syl, client)
                syl.year_1_summary_he = data.get("year_1")
                syl.year_2_summary_he = data.get("year_2")
                syl.year_3_summary_he = data.get("year_3")
                syl.one_line_pitch_he = data.get("one_line_pitch")
                syl.summarized_at = datetime.now(timezone.utc)
                summarised += 1
                log.info("summarize.success", syllabus_id=str(syl.id))
            except Exception as exc:
                errors += 1
                log.exception(
                    "summarize.error",
                    syllabus_id=str(syl.id),
                    error=str(exc),
                )

        await db.commit()

    log.info(
        "summarize.batch_complete",
        summarised=summarised,
        skipped=skipped,
        errors=errors,
    )
    return {"summarised": summarised, "skipped": skipped, "errors": errors}


# ── Celery task ───────────────────────────────────────────────────────────────


@celery_app.task(
    name="scraper.tasks.summarize.summarise_syllabi",
    bind=True,
    max_retries=0,
    acks_late=True,
)
def summarise_syllabi(self) -> dict:  # noqa: ANN001
    """
    Celery task: summarise up to 10 unsummarised syllabi per invocation.

    Uses claude-haiku for fast, cost-efficient batch processing.
    Scheduled nightly at 01:00 UTC by Celery Beat.
    """
    return asyncio.run(_run_batch())
