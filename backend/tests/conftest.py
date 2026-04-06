"""
Shared test fixtures for all router tests.

Strategy
--------
* DB is mocked via FastAPI dependency_overrides — no real Postgres needed.
* Redis cache is patched at the `app.core.cache` module level so the cache
  module reference used inside routers is always the patched version.
* Factory helpers (make_*) return SimpleNamespace objects; Pydantic's
  `from_attributes=True` treats them exactly like ORM model instances.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core import cache as cache_module
from app.core.database import get_db
from app.core.enums import DemandTrend, InstitutionType, ScrapeStatus
from app.main import app

# ── Shared identifiers ────────────────────────────────────────────────────────

INST_ID = "TAU"
PROGRAM_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
FORMULA_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
SYLLABUS_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CAREER_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
SCRAPE_RUN_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")

NOW = datetime(2026, 4, 5, 12, 0, 0, tzinfo=timezone.utc)


# ── ORM mock factories ────────────────────────────────────────────────────────

def make_institution(**kw) -> SimpleNamespace:
    defaults = dict(
        id=INST_ID,
        name_he="אוניברסיטת תל אביב",
        name_en="Tel Aviv University",
        type=InstitutionType.university,
        location="תל אביב",
        city="Tel Aviv",
        website_url="https://www.tau.ac.il",
        is_active=True,
        created_at=NOW,
    )
    return SimpleNamespace(**{**defaults, **kw})


def make_program(**kw) -> SimpleNamespace:
    defaults = dict(
        id=PROGRAM_ID,
        institution_id=INST_ID,
        name_he="מדעי המחשב",
        name_en="Computer Science",
        field="computer_science",
        degree_type="BSc",
        duration_years=3,
        location="תל אביב",
        tuition_annual_ils=12000,
        official_url="https://www.tau.ac.il/cs",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
        # Relationship stubs (overridden per test where needed)
        institution=None,
        sekem_formulas=[],
        syllabi=[],
        career_data=[],
    )
    return SimpleNamespace(**{**defaults, **kw})


def make_sekem_formula(**kw) -> SimpleNamespace:
    defaults = dict(
        id=FORMULA_ID,
        program_id=PROGRAM_ID,
        year=2025,
        bagrut_weight=4.0,
        psychometric_weight=0.5,
        threshold_sekem=680.0,
        subject_bonuses=[],
        bagrut_requirements=[],
        scraped_at=NOW,
        source_url="https://www.tau.ac.il/cs/admission",
    )
    return SimpleNamespace(**{**defaults, **kw})


def make_syllabus(**kw) -> SimpleNamespace:
    defaults = dict(
        id=SYLLABUS_ID,
        program_id=PROGRAM_ID,
        year_1_summary_he="שנה ראשונה — בסיסי מדעי המחשב",
        year_2_summary_he=None,
        year_3_summary_he=None,
        core_courses=["מבנה נתונים", "אלגוריתמים"],
        elective_tracks=["בינה מלאכותית"],
        one_line_pitch_he="תכנית מאתגרת ומובילה",
        raw_html="<html>...</html>",
        summarized_at=NOW,
        scraped_at=NOW,
    )
    return SimpleNamespace(**{**defaults, **kw})


def make_career_data(**kw) -> SimpleNamespace:
    defaults = dict(
        id=CAREER_ID,
        program_id=PROGRAM_ID,
        job_titles=["מפתח תוכנה", "מהנדס DevOps"],
        avg_salary_min_ils=18_000,
        avg_salary_max_ils=35_000,
        demand_trend=DemandTrend.growing,
        data_year=2025,
        source="CBS",
        updated_at=NOW,
    )
    return SimpleNamespace(**{**defaults, **kw})


def make_scrape_run(**kw) -> SimpleNamespace:
    defaults = dict(
        id=SCRAPE_RUN_ID,
        institution_id=INST_ID,
        started_at=NOW,
        completed_at=NOW,
        status=ScrapeStatus.success,
        records_updated=42,
        anomaly_flag=False,
        error_log=None,
    )
    return SimpleNamespace(**{**defaults, **kw})


# ── DB session mock ───────────────────────────────────────────────────────────

@pytest.fixture()
def mock_session() -> AsyncMock:
    """Async mock of an SQLAlchemy AsyncSession."""
    session = AsyncMock()
    # Make the mock usable as an async context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture(autouse=True)
def override_db(mock_session: AsyncMock):
    """Replace get_db with a generator that yields mock_session."""

    async def _override():
        yield mock_session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)


# ── Cache mock ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def disable_cache(monkeypatch):
    """
    Default: cache always misses (cache_get returns None), cache_set is a no-op.
    Individual tests can override by re-patching cache_module.cache_get.
    """
    monkeypatch.setattr(cache_module, "cache_get", AsyncMock(return_value=None))
    monkeypatch.setattr(cache_module, "cache_set", AsyncMock(return_value=None))
    monkeypatch.setattr(cache_module, "_scan_delete", AsyncMock(return_value=None))


# ── HTTP client ───────────────────────────────────────────────────────────────

@pytest.fixture()
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
