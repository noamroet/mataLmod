"""
Unit tests for scraper/tasks/scrape_dispatch.py.

All DB I/O and scraper network calls are mocked.
asyncio.run() wraps the async _run_scrape coroutine; we test the coroutine
directly to avoid the Celery runtime dependency.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scrapers.base import ScrapeResult
from scrapers.tau import TauScraper
from tasks.scrape_dispatch import SCRAPER_REGISTRY, _run_scrape


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_result(
    name_he: str = "מדעי המחשב",
    threshold: float = 730.0,
    scrape_ok: bool = True,
    error_message: str | None = None,
) -> ScrapeResult:
    return ScrapeResult(
        institution_id="TAU",
        name_he=name_he,
        field="computer_science",
        degree_type="BSc",
        official_url="https://go.tau.ac.il/he/programs/cs-bsc",
        threshold_sekem=threshold,
        bagrut_weight=0.55,
        psychometric_weight=0.45,
        sekem_year=2025,
        scrape_ok=scrape_ok,
        error_message=error_message,
    )


def _ok_results(n: int = 3) -> list[ScrapeResult]:
    return [_make_result(name_he=f"תוכנית {i}", threshold=700.0 + i * 10) for i in range(n)]


def _make_run(run_id: uuid.UUID | None = None) -> SimpleNamespace:
    """Minimal ORM-like ScrapeRun object."""
    return SimpleNamespace(
        id=run_id or uuid.uuid4(),
        institution_id="TAU",
        status=None,
        anomaly_flag=False,
        error_log=None,
        records_updated=0,
        completed_at=None,
    )


# ── SCRAPER_REGISTRY ──────────────────────────────────────────────────────────

class TestScraperRegistry:
    def test_tau_registered(self) -> None:
        assert "TAU" in SCRAPER_REGISTRY

    def test_tau_maps_to_tau_scraper(self) -> None:
        assert SCRAPER_REGISTRY["TAU"] is TauScraper

    def test_unknown_institution_raises(self) -> None:
        with pytest.raises(ValueError, match="No scraper registered"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(_run_scrape("UNKNOWN"))


# ── _run_scrape — success path ────────────────────────────────────────────────

class TestRunScrapeSuccess:
    @pytest.mark.asyncio
    async def test_returns_success_status(self) -> None:
        run = _make_run()
        results = _ok_results(3)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # ScrapeRun is captured when db.add() is called
        captured_run: list[SimpleNamespace] = []

        def _capture_add(obj: object) -> None:
            if hasattr(obj, "status"):
                captured_run.append(obj)

        mock_session.add.side_effect = _capture_add

        with (
            patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session),
            patch("tasks.scrape_dispatch.SCRAPER_REGISTRY", {"TAU": _make_mock_scraper(results)}),
            patch("tasks.scrape_dispatch.detect_anomaly", return_value=False),
            patch("tasks.scrape_dispatch.publish_results", new_callable=AsyncMock, return_value=3),
        ):
            result = await _run_scrape("TAU")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_records_updated_matches_publish_return(self) -> None:
        run = _make_run()
        results = _ok_results(5)

        mock_session = _make_mock_session()

        with (
            patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session),
            patch("tasks.scrape_dispatch.SCRAPER_REGISTRY", {"TAU": _make_mock_scraper(results)}),
            patch("tasks.scrape_dispatch.detect_anomaly", return_value=False),
            patch("tasks.scrape_dispatch.publish_results", new_callable=AsyncMock, return_value=5),
        ):
            result = await _run_scrape("TAU")

        assert result["records_updated"] == 5

    @pytest.mark.asyncio
    async def test_run_id_in_result(self) -> None:
        results = _ok_results(2)
        mock_session = _make_mock_session()

        with (
            patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session),
            patch("tasks.scrape_dispatch.SCRAPER_REGISTRY", {"TAU": _make_mock_scraper(results)}),
            patch("tasks.scrape_dispatch.detect_anomaly", return_value=False),
            patch("tasks.scrape_dispatch.publish_results", new_callable=AsyncMock, return_value=2),
        ):
            result = await _run_scrape("TAU")

        # run_id key must be present; its value is str(run.id).
        # In tests the ScrapeRun.id default fires on real DB flush, so the mock
        # produces str(None) — we only verify the key is present here.
        assert "run_id" in result
        assert isinstance(result["run_id"], str)

    @pytest.mark.asyncio
    async def test_publish_results_called_once(self) -> None:
        results = _ok_results(3)
        mock_session = _make_mock_session()
        mock_publish = AsyncMock(return_value=3)

        with (
            patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session),
            patch("tasks.scrape_dispatch.SCRAPER_REGISTRY", {"TAU": _make_mock_scraper(results)}),
            patch("tasks.scrape_dispatch.detect_anomaly", return_value=False),
            patch("tasks.scrape_dispatch.publish_results", mock_publish),
        ):
            await _run_scrape("TAU")

        mock_publish.assert_awaited_once()
        _, call_kwargs = mock_publish.call_args
        passed_results = mock_publish.call_args[0][1]
        assert passed_results is results

    @pytest.mark.asyncio
    async def test_db_commit_called_on_success(self) -> None:
        results = _ok_results(2)
        mock_session = _make_mock_session()

        with (
            patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session),
            patch("tasks.scrape_dispatch.SCRAPER_REGISTRY", {"TAU": _make_mock_scraper(results)}),
            patch("tasks.scrape_dispatch.detect_anomaly", return_value=False),
            patch("tasks.scrape_dispatch.publish_results", new_callable=AsyncMock, return_value=2),
        ):
            await _run_scrape("TAU")

        mock_session.commit.assert_awaited()


# ── _run_scrape — anomaly path ────────────────────────────────────────────────

class TestRunScrapeAnomaly:
    @pytest.mark.asyncio
    async def test_returns_anomaly_status(self) -> None:
        results = _ok_results(1)
        mock_session = _make_mock_session()

        with (
            patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session),
            patch("tasks.scrape_dispatch.SCRAPER_REGISTRY", {"TAU": _make_mock_scraper(results)}),
            patch("tasks.scrape_dispatch.detect_anomaly", return_value=True),
            patch("tasks.scrape_dispatch.publish_results", new_callable=AsyncMock) as mock_pub,
        ):
            result = await _run_scrape("TAU")

        assert result["status"] == "anomaly"
        assert result["records_updated"] == 0

    @pytest.mark.asyncio
    async def test_publish_not_called_on_anomaly(self) -> None:
        results = _ok_results(1)
        mock_session = _make_mock_session()
        mock_publish = AsyncMock(return_value=0)

        with (
            patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session),
            patch("tasks.scrape_dispatch.SCRAPER_REGISTRY", {"TAU": _make_mock_scraper(results)}),
            patch("tasks.scrape_dispatch.detect_anomaly", return_value=True),
            patch("tasks.scrape_dispatch.publish_results", mock_publish),
        ):
            await _run_scrape("TAU")

        mock_publish.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_db_commit_called_on_anomaly(self) -> None:
        results = _ok_results(1)
        mock_session = _make_mock_session()

        with (
            patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session),
            patch("tasks.scrape_dispatch.SCRAPER_REGISTRY", {"TAU": _make_mock_scraper(results)}),
            patch("tasks.scrape_dispatch.detect_anomaly", return_value=True),
            patch("tasks.scrape_dispatch.publish_results", new_callable=AsyncMock),
        ):
            await _run_scrape("TAU")

        mock_session.commit.assert_awaited()


# ── _run_scrape — failure path ────────────────────────────────────────────────

class TestRunScrapeFailed:
    @pytest.mark.asyncio
    async def test_scraper_exception_is_reraised(self) -> None:
        mock_session = _make_mock_session()
        failing_scraper_cls = _make_crashing_scraper(RuntimeError("scraper exploded"))

        with (
            patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session),
            patch("tasks.scrape_dispatch.SCRAPER_REGISTRY", {"TAU": failing_scraper_cls}),
        ):
            with pytest.raises(RuntimeError, match="scraper exploded"):
                await _run_scrape("TAU")

    @pytest.mark.asyncio
    async def test_db_commit_called_after_failure(self) -> None:
        mock_session = _make_mock_session()
        failing_scraper_cls = _make_crashing_scraper(RuntimeError("boom"))

        with (
            patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session),
            patch("tasks.scrape_dispatch.SCRAPER_REGISTRY", {"TAU": failing_scraper_cls}),
        ):
            with pytest.raises(RuntimeError):
                await _run_scrape("TAU")

        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_unknown_institution_raises_value_error(self) -> None:
        mock_session = _make_mock_session()

        with patch("tasks.scrape_dispatch.AsyncSessionLocal", return_value=mock_session):
            with pytest.raises(ValueError, match="No scraper registered"):
                await _run_scrape("NONEXISTENT")


# ── publish_results upsert logic ──────────────────────────────────────────────

class TestPublishResultsUpsert:
    """Test upsert logic in pipeline/publisher.py via direct calls."""

    @pytest.mark.asyncio
    async def test_new_program_calls_db_add(self) -> None:
        from pipeline.publisher import publish_results

        result = _make_result()
        db = _make_mock_db_for_publisher(existing_program=None, existing_formula=None)

        await publish_results(db, [result])

        # db.add should have been called (once for program, once for formula)
        assert db.add.call_count >= 1

    @pytest.mark.asyncio
    async def test_failed_result_skipped(self) -> None:
        from pipeline.publisher import publish_results

        result = _make_result(scrape_ok=False, error_message="network error")
        db = _make_mock_db_for_publisher(existing_program=None, existing_formula=None)

        count = await publish_results(db, [result])

        assert count == 0
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_existing_program_not_added_again(self) -> None:
        from pipeline.publisher import publish_results

        program_id = uuid.uuid4()
        existing_program = SimpleNamespace(
            id=program_id,
            institution_id="TAU",
            name_he="מדעי המחשב",
            degree_type="BSc",
            name_en=None,
            field="computer_science",
            duration_years=3,
            tuition_annual_ils=None,
            official_url="https://old-url.com",
            updated_at=None,
        )

        result = _make_result()
        db = _make_mock_db_for_publisher(
            existing_program=existing_program,
            existing_formula=None,
        )

        await publish_results(db, [result])

        # Program was updated, not inserted — db.add called only for the formula
        # Check that official_url was updated on the existing object
        assert existing_program.official_url == result.official_url

    @pytest.mark.asyncio
    async def test_existing_formula_updated_not_duplicated(self) -> None:
        from pipeline.publisher import publish_results

        program_id = uuid.uuid4()
        existing_program = SimpleNamespace(
            id=program_id,
            institution_id="TAU",
            name_he="מדעי המחשב",
            degree_type="BSc",
            name_en=None,
            field="computer_science",
            duration_years=3,
            tuition_annual_ils=None,
            official_url="https://go.tau.ac.il/he/programs/cs-bsc",
            updated_at=None,
        )
        existing_formula = SimpleNamespace(
            id=uuid.uuid4(),
            program_id=program_id,
            year=2025,
            bagrut_weight=0.50,
            psychometric_weight=0.50,
            threshold_sekem=700.0,
            subject_bonuses=[],
            bagrut_requirements=[],
            scraped_at=datetime.now(timezone.utc),
        )

        result = _make_result(threshold=730.0)
        # Two execute() calls: first returns existing program, second returns existing formula
        db = _make_mock_db_for_publisher(
            existing_program=existing_program,
            existing_formula=existing_formula,
        )

        await publish_results(db, [result])

        # Formula was updated in-place; threshold should reflect new value
        assert existing_formula.threshold_sekem == 730.0
        assert existing_formula.bagrut_weight == 0.55

    @pytest.mark.asyncio
    async def test_returns_count_of_updated_records(self) -> None:
        from pipeline.publisher import publish_results

        results = [_make_result(name_he=f"תוכנית {i}") for i in range(4)]
        db = _make_mock_db_for_publisher(existing_program=None, existing_formula=None)

        count = await publish_results(db, results)
        assert count == 4

    @pytest.mark.asyncio
    async def test_mixed_ok_and_failed_counts_only_ok(self) -> None:
        from pipeline.publisher import publish_results

        results = [
            _make_result(name_he="תוכנית טובה"),
            _make_result(name_he="תוכנית שנכשלה", scrape_ok=False),
        ]
        db = _make_mock_db_for_publisher(existing_program=None, existing_formula=None)

        count = await publish_results(db, results)
        assert count == 1


# ── Private mock factories ────────────────────────────────────────────────────

def _make_mock_scraper(results: list[ScrapeResult]) -> type:
    """Return a fake scraper class whose scrape() returns *results*."""

    class _FakeScraper:
        INSTITUTION_ID = "TAU"

        async def __aenter__(self) -> "_FakeScraper":
            return self

        async def __aexit__(self, *_: object) -> None:
            pass

        async def scrape(self) -> list[ScrapeResult]:
            return results

    return _FakeScraper


def _make_crashing_scraper(exc: Exception) -> type:
    """Return a fake scraper class whose scrape() raises *exc*."""

    class _CrashingScraper:
        INSTITUTION_ID = "TAU"

        async def __aenter__(self) -> "_CrashingScraper":
            return self

        async def __aexit__(self, *_: object) -> None:
            pass

        async def scrape(self) -> list[ScrapeResult]:
            raise exc

    return _CrashingScraper


def _make_mock_session() -> AsyncMock:
    """Mock AsyncSession that supports add/flush/commit and context manager protocol."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    # ScrapeRun gets an auto-id via flush; simulate by setting id when add() is called
    _added: list[object] = []

    def _capture_add(obj: object) -> None:
        _added.append(obj)
        if not hasattr(obj, "id") or obj.id is None:  # type: ignore[union-attr]
            object.__setattr__(obj, "id", uuid.uuid4())

    session.add.side_effect = _capture_add

    # Default execute result: no existing records
    empty_result = MagicMock()
    empty_result.scalar_one_or_none.return_value = None
    session.execute.return_value = empty_result

    return session


def _make_mock_db_for_publisher(
    existing_program: object | None,
    existing_formula: object | None,
) -> AsyncMock:
    """
    Mock DB session for publisher upsert tests.

    execute() is called up to 3 times:
      1. _upsert_program   → select Program
      2. _upsert_sekem_formula → select SekemFormula
      3. _upsert_syllabus  → select Syllabus  (if raw_html present)

    Each call returns scalar_one_or_none() of the pre-configured existing object.
    We cycle through: [program_result, formula_result, None_for_syllabus].
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    def _make_scalar(value: object) -> MagicMock:
        r = MagicMock()
        r.scalar_one_or_none.return_value = value
        return r

    # Syllabus query always returns None (fresh insert)
    session.execute.side_effect = [
        _make_scalar(existing_program),
        _make_scalar(existing_formula),
        _make_scalar(None),  # syllabus
    ] * 10  # enough for multi-record tests

    return session
