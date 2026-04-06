"""
Shared fixtures for scraper tests.

HTML fixtures are loaded from tests/fixtures/ once per session.
DB session is mocked with AsyncMock — no Postgres required.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
# Ensure both backend/ and scraper/ are importable.
_HERE = Path(__file__).resolve().parent
_SCRAPER_ROOT = _HERE.parent
_BACKEND_ROOT = _SCRAPER_ROOT.parent / "backend"
for _p in [str(_SCRAPER_ROOT), str(_BACKEND_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

FIXTURES = _HERE / "fixtures"

# ── HTML fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def tau_list_html() -> str:
    return (FIXTURES / "tau_programs_list.html").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def tau_detail_html() -> str:
    return (FIXTURES / "tau_program_detail.html").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def tau_detail_minimal_html() -> str:
    return (FIXTURES / "tau_program_detail_minimal.html").read_text(encoding="utf-8")


# ── Mock DB session ───────────────────────────────────────────────────────────

@pytest.fixture()
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    # Default: no existing records found (all upserts become inserts)
    empty_result = MagicMock()
    empty_result.scalar_one_or_none.return_value = None
    session.execute.return_value = empty_result
    return session


# ── ORM mock factories ────────────────────────────────────────────────────────

def make_program(name_he: str = "מדעי המחשב", **kw) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        institution_id="TAU",
        name_he=name_he,
        name_en="Computer Science",
        field="computer_science",
        degree_type="BSc",
        duration_years=3,
        location="תל אביב",
        tuition_annual_ils=12480,
        official_url="https://go.tau.ac.il/he/programs/cs-bsc",
        is_active=True,
        **kw,
    )


def make_formula(**kw) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        program_id=uuid.uuid4(),
        year=2025,
        bagrut_weight=0.55,
        psychometric_weight=0.45,
        threshold_sekem=730.0,
        subject_bonuses=[],
        bagrut_requirements=[],
        **kw,
    )
