"""
Unit tests for the TAU scraper.

All tests use saved HTML fixtures — no live network requests.
fetch_dynamic is patched to return fixture HTML.
"""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from scrapers.base import (
    ANOMALY_THRESHOLD,
    ScrapeResult,
    check_structure_integrity,
    page_checksum,
    structural_similarity,
)
from scrapers.tau import (
    BASE_URL,
    EXPECTED_DETAIL_SELECTORS,
    EXPECTED_LIST_SELECTORS,
    INSTITUTION_ID,
    TauScraper,
    _ProgramEntry,
    _map_field,
    _normalize_degree_type,
    parse_program_detail,
    parse_programs_list,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_entry(
    name_he: str = "מדעי המחשב",
    faculty: str = "בית הספר למדעי המחשב",
    degree_raw: str = "B.Sc",
    url: str = "https://go.tau.ac.il/he/programs/cs-bsc",
) -> _ProgramEntry:
    return _ProgramEntry(name_he=name_he, faculty=faculty, degree_raw=degree_raw, url=url)


# ── parse_programs_list ───────────────────────────────────────────────────────

class TestParseProgramsList:
    def test_returns_five_programs(self, tau_list_html: str) -> None:
        entries = parse_programs_list(tau_list_html)
        assert len(entries) == 5

    def test_first_program_name(self, tau_list_html: str) -> None:
        entries = parse_programs_list(tau_list_html)
        assert entries[0].name_he == "מדעי המחשב"

    def test_url_is_absolute(self, tau_list_html: str) -> None:
        entries = parse_programs_list(tau_list_html)
        for entry in entries:
            assert entry.url.startswith("https://")

    def test_relative_href_becomes_absolute(self, tau_list_html: str) -> None:
        # All fixture hrefs are relative (/he/programs/...)
        entries = parse_programs_list(tau_list_html)
        assert entries[0].url == BASE_URL + "/he/programs/cs-bsc"

    def test_degree_types_extracted(self, tau_list_html: str) -> None:
        entries = parse_programs_list(tau_list_html)
        degrees = {e.degree_raw for e in entries}
        assert "B.Sc" in degrees
        assert "LL.B" in degrees
        assert "B.Ed" in degrees

    def test_faculties_extracted(self, tau_list_html: str) -> None:
        entries = parse_programs_list(tau_list_html)
        assert entries[0].faculty == "בית הספר למדעי המחשב"

    def test_empty_html_returns_empty_list(self) -> None:
        assert parse_programs_list("<html><body></body></html>") == []

    def test_card_without_link_is_skipped(self) -> None:
        html = """
        <div class="program-card">
          <!-- no .program-card__link -->
          <span class="program-card__degree">B.A</span>
        </div>
        """
        assert parse_programs_list(html) == []

    def test_all_program_names_populated(self, tau_list_html: str) -> None:
        entries = parse_programs_list(tau_list_html)
        for entry in entries:
            assert entry.name_he, f"Empty name_he for {entry}"


# ── parse_program_detail ──────────────────────────────────────────────────────

class TestParseProgramDetail:
    def test_threshold_extracted(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert result.threshold_sekem == 730.0

    def test_bagrut_weight_extracted(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert result.bagrut_weight == 0.55

    def test_psychometric_weight_extracted(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert result.psychometric_weight == 0.45

    def test_uses_highest_year_row(self, tau_detail_html: str) -> None:
        # Fixture has 2024 (720) and 2025 (730); should pick 2025
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert result.sekem_year == 2025
        assert result.threshold_sekem == 730.0

    def test_two_subject_bonuses_extracted(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert len(result.subject_bonuses) == 2

    def test_math_bonus_correct(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        math_bonus = next(b for b in result.subject_bonuses if b["subject_code"] == "math")
        assert math_bonus["units"] == 5
        assert math_bonus["bonus_points"] == 10.0

    def test_physics_bonus_correct(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        phys_bonus = next(b for b in result.subject_bonuses if b["subject_code"] == "physics")
        assert phys_bonus["units"] == 5
        assert phys_bonus["bonus_points"] == 5.0

    def test_two_bagrut_requirements_extracted(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert len(result.bagrut_requirements) == 2

    def test_math_requirement_mandatory(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        math_req = next(r for r in result.bagrut_requirements if r["subject_code"] == "math")
        assert math_req["min_units"] == 4
        assert math_req["min_grade"] == 70
        assert math_req["mandatory"] is True

    def test_english_requirement_not_mandatory(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        en_req = next(r for r in result.bagrut_requirements if r["subject_code"] == "english")
        assert en_req["mandatory"] is False

    def test_tuition_extracted(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert result.tuition_annual_ils == 12480

    def test_duration_extracted(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert result.duration_years == 3

    def test_degree_type_bsc(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert result.degree_type == "BSc"

    def test_field_computer_science(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert result.field == "computer_science"

    def test_institution_id_is_tau(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert result.institution_id == INSTITUTION_ID

    def test_scrape_ok_true(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert result.scrape_ok is True

    def test_raw_html_captured(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert "syllabus-section" in result.raw_html

    def test_page_checksum_populated(self, tau_detail_html: str) -> None:
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry)
        assert len(result.page_checksum) == 64  # SHA-256 hex

    def test_official_url_from_entry(self, tau_detail_html: str) -> None:
        entry = _make_entry(url="https://go.tau.ac.il/he/programs/cs-bsc")
        result = parse_program_detail(tau_detail_html, entry)
        assert result.official_url == "https://go.tau.ac.il/he/programs/cs-bsc"

    def test_scrape_year_override(self, tau_detail_html: str) -> None:
        # scrape_year param is overridden by the page's data-year when present
        entry = _make_entry()
        result = parse_program_detail(tau_detail_html, entry, scrape_year=2020)
        # Page has data-year="2025", so that wins
        assert result.sekem_year == 2025


class TestParseProgramDetailMinimal:
    def test_threshold_defaults_to_zero(self, tau_detail_minimal_html: str) -> None:
        entry = _make_entry(
            name_he="מינהל עסקים",
            faculty="הפקולטה לניהול",
            degree_raw="B.A",
            url="https://go.tau.ac.il/he/programs/ba-management",
        )
        result = parse_program_detail(tau_detail_minimal_html, entry)
        assert result.threshold_sekem == 0.0

    def test_tuition_is_none(self, tau_detail_minimal_html: str) -> None:
        entry = _make_entry(name_he="מינהל עסקים", faculty="הפקולטה לניהול", degree_raw="B.A",
                            url="https://go.tau.ac.il/he/programs/ba-management")
        result = parse_program_detail(tau_detail_minimal_html, entry)
        assert result.tuition_annual_ils is None

    def test_no_bonuses(self, tau_detail_minimal_html: str) -> None:
        entry = _make_entry(name_he="מינהל עסקים", faculty="הפקולטה לניהול", degree_raw="B.A",
                            url="https://go.tau.ac.il/he/programs/ba-management")
        result = parse_program_detail(tau_detail_minimal_html, entry)
        assert result.subject_bonuses == []

    def test_no_requirements(self, tau_detail_minimal_html: str) -> None:
        entry = _make_entry(name_he="מינהל עסקים", faculty="הפקולטה לניהול", degree_raw="B.A",
                            url="https://go.tau.ac.il/he/programs/ba-management")
        result = parse_program_detail(tau_detail_minimal_html, entry)
        assert result.bagrut_requirements == []

    def test_syllabus_raw_html_present(self, tau_detail_minimal_html: str) -> None:
        entry = _make_entry(name_he="מינהל עסקים", faculty="הפקולטה לניהול", degree_raw="B.A",
                            url="https://go.tau.ac.il/he/programs/ba-management")
        result = parse_program_detail(tau_detail_minimal_html, entry)
        assert "syllabus-section" in result.raw_html

    def test_scrape_ok_still_true(self, tau_detail_minimal_html: str) -> None:
        entry = _make_entry(name_he="מינהל עסקים", faculty="הפקולטה לניהול", degree_raw="B.A",
                            url="https://go.tau.ac.il/he/programs/ba-management")
        result = parse_program_detail(tau_detail_minimal_html, entry)
        assert result.scrape_ok is True


# ── _map_field ────────────────────────────────────────────────────────────────

class TestMapField:
    @pytest.mark.parametrize("faculty,expected", [
        ("בית הספר למדעי המחשב", "computer_science"),
        ("הפקולטה להנדסה חשמל", "electrical_engineering"),
        ("הפקולטה למשפטים", "law"),
        ("הפקולטה לניהול", "business"),
        ("בית הספר לחינוך", "education"),
        ("הפקולטה לרפואה", "medicine"),
        ("הפקולטה לפסיכולוגיה", "psychology"),
        ("הפקולטה למדעי הרוח", "humanities"),
        ("הפקולטה לאמנות", "arts_design"),
        ("הפקולטה לתקשורת", "communication"),
    ])
    def test_known_faculty_mapping(self, faculty: str, expected: str) -> None:
        assert _map_field(faculty) == expected

    def test_unknown_faculty_returns_other(self) -> None:
        assert _map_field("הפקולטה לדברים שונים") == "other"

    def test_program_name_used_as_fallback(self) -> None:
        # Empty faculty, but program name contains keyword
        assert _map_field("", "מדעי המחשב") == "computer_science"

    def test_combined_faculty_and_name(self) -> None:
        # Faculty alone doesn't match, but combined text does
        assert _map_field("הפקולטה למדעים", "מדעי המחשב") == "computer_science"

    def test_mathematics_mapping(self) -> None:
        assert _map_field("מחלקת מתמטיקה") == "mathematics"

    def test_physics_chemistry_mapping(self) -> None:
        assert _map_field("מחלקת פיזיקה") == "physics_chemistry"


# ── _normalize_degree_type ────────────────────────────────────────────────────

class TestNormalizeDegreeType:
    @pytest.mark.parametrize("raw,expected", [
        ("B.Sc", "BSc"),
        ("BSc", "BSc"),
        ("b.sc", "BSc"),
        ("LL.B", "LLB"),
        ("llb", "LLB"),
        ("B.Ed", "BEd"),
        ("BEd", "BEd"),
        ("B.Arch", "BArch"),
        ("BArch", "BArch"),
        ("B.F.A", "BFA"),
        ("BFA", "BFA"),
        ("B.A", "BA"),
        ("BA", "BA"),
        ("תואר בוגר", "BA"),  # Hebrew fallback → BA
        ("", "BA"),  # Empty fallback → BA
    ])
    def test_normalize(self, raw: str, expected: str) -> None:
        assert _normalize_degree_type(raw) == expected

    def test_hebrew_science_word(self) -> None:
        # "מדע" in the degree string → BSc
        assert _normalize_degree_type("תואר מדע") == "BSc"

    def test_hebrew_law_word(self) -> None:
        assert _normalize_degree_type("תואר משפטים") == "LLB"

    def test_hebrew_education_word(self) -> None:
        assert _normalize_degree_type("תואר חינוך") == "BEd"


# ── ScrapeResult validation ───────────────────────────────────────────────────

class TestScrapeResultValidation:
    def test_invalid_field_coerced_to_other(self) -> None:
        r = ScrapeResult(
            institution_id="TAU",
            name_he="test",
            field="totally_invalid_field",
            official_url="https://example.com",
        )
        assert r.field == "other"

    def test_valid_field_accepted(self) -> None:
        r = ScrapeResult(
            institution_id="TAU",
            name_he="test",
            field="computer_science",
            official_url="https://example.com",
        )
        assert r.field == "computer_science"

    def test_invalid_degree_type_coerced_to_ba(self) -> None:
        r = ScrapeResult(
            institution_id="TAU",
            name_he="test",
            degree_type="XYZ",
            official_url="https://example.com",
        )
        assert r.degree_type == "BA"

    def test_valid_degree_types_accepted(self) -> None:
        for dt in ["BA", "BSc", "BEd", "BArch", "BFA", "LLB"]:
            r = ScrapeResult(
                institution_id="TAU",
                name_he="test",
                degree_type=dt,
                official_url="https://example.com",
            )
            assert r.degree_type == dt

    def test_weight_out_of_range_raises(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="Weight must be in"):
            ScrapeResult(
                institution_id="TAU",
                name_he="test",
                official_url="https://example.com",
                bagrut_weight=1.5,
            )

    def test_negative_weight_raises(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="Weight must be in"):
            ScrapeResult(
                institution_id="TAU",
                name_he="test",
                official_url="https://example.com",
                psychometric_weight=-0.1,
            )

    def test_boundary_weights_accepted(self) -> None:
        r = ScrapeResult(
            institution_id="TAU",
            name_he="test",
            official_url="https://example.com",
            bagrut_weight=0.0,
            psychometric_weight=1.0,
        )
        assert r.bagrut_weight == 0.0
        assert r.psychometric_weight == 1.0

    def test_scrape_ok_defaults_true(self) -> None:
        r = ScrapeResult(institution_id="TAU", name_he="test", official_url="https://example.com")
        assert r.scrape_ok is True

    def test_whitespace_stripped(self) -> None:
        r = ScrapeResult(institution_id="  TAU  ", name_he="  test  ", official_url="https://x.com")
        assert r.institution_id == "TAU"
        assert r.name_he == "test"


# ── page_checksum / structural integrity ─────────────────────────────────────

class TestStructuralHelpers:
    def test_checksum_is_64_hex_chars(self, tau_detail_html: str) -> None:
        cs = page_checksum(tau_detail_html)
        assert len(cs) == 64
        assert all(c in "0123456789abcdef" for c in cs)

    def test_same_html_same_checksum(self, tau_detail_html: str) -> None:
        assert page_checksum(tau_detail_html) == page_checksum(tau_detail_html)

    def test_different_html_different_checksum(
        self, tau_detail_html: str, tau_list_html: str
    ) -> None:
        assert page_checksum(tau_detail_html) != page_checksum(tau_list_html)

    def test_structural_similarity_identical(self, tau_detail_html: str) -> None:
        assert structural_similarity(tau_detail_html, tau_detail_html) == 1.0

    def test_structural_similarity_empty_baseline(self, tau_detail_html: str) -> None:
        # Empty baseline → always returns 1.0
        assert structural_similarity(tau_detail_html, "") == 1.0

    def test_structural_similarity_different_pages(
        self, tau_detail_html: str, tau_list_html: str
    ) -> None:
        sim = structural_similarity(tau_detail_html, tau_list_html)
        # Different pages share some tags (html, head, body) but not all
        assert 0.0 < sim < 1.0

    def test_check_structure_integrity_all_present(self, tau_detail_html: str) -> None:
        coverage = check_structure_integrity(tau_detail_html, EXPECTED_DETAIL_SELECTORS)
        assert coverage == 1.0

    def test_check_structure_integrity_list_page(self, tau_list_html: str) -> None:
        coverage = check_structure_integrity(tau_list_html, EXPECTED_LIST_SELECTORS)
        assert coverage == 1.0

    def test_check_structure_integrity_missing_selectors(self) -> None:
        html = "<html><body><div class='some-other-class'></div></body></html>"
        coverage = check_structure_integrity(html, EXPECTED_DETAIL_SELECTORS)
        assert coverage == 0.0

    def test_check_structure_integrity_empty_selectors(self, tau_detail_html: str) -> None:
        # No selectors to check → always 1.0
        assert check_structure_integrity(tau_detail_html, []) == 1.0

    def test_above_anomaly_threshold(self, tau_detail_html: str) -> None:
        coverage = check_structure_integrity(tau_detail_html, EXPECTED_DETAIL_SELECTORS)
        assert coverage >= (1.0 - ANOMALY_THRESHOLD)


# ── TauScraper.scrape() ───────────────────────────────────────────────────────

class TestTauScraper:
    """Integration-style tests using mocked fetch_dynamic (no live requests)."""

    @pytest.mark.asyncio
    async def test_scrape_returns_five_results(
        self, tau_list_html: str, tau_detail_html: str
    ) -> None:
        scraper = TauScraper()
        # First call → list page; subsequent calls → detail page for each program
        fetch_calls = [tau_list_html] + [tau_detail_html] * 5
        scraper.fetch_dynamic = AsyncMock(side_effect=fetch_calls)

        results = await scraper.scrape()
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_all_results_scrape_ok(
        self, tau_list_html: str, tau_detail_html: str
    ) -> None:
        scraper = TauScraper()
        scraper.fetch_dynamic = AsyncMock(
            side_effect=[tau_list_html] + [tau_detail_html] * 5
        )

        results = await scraper.scrape()
        assert all(r.scrape_ok for r in results)

    @pytest.mark.asyncio
    async def test_all_results_have_tau_institution_id(
        self, tau_list_html: str, tau_detail_html: str
    ) -> None:
        scraper = TauScraper()
        scraper.fetch_dynamic = AsyncMock(
            side_effect=[tau_list_html] + [tau_detail_html] * 5
        )

        results = await scraper.scrape()
        assert all(r.institution_id == "TAU" for r in results)

    @pytest.mark.asyncio
    async def test_failed_detail_page_produces_scrape_ok_false(
        self, tau_list_html: str
    ) -> None:
        scraper = TauScraper()

        async def _fetch_side_effect(url: str) -> str:
            if "undergraduate" in url:
                return tau_list_html
            raise ConnectionError("network error")

        scraper.fetch_dynamic = AsyncMock(side_effect=_fetch_side_effect)

        results = await scraper.scrape()
        # All 5 programs fail on detail fetch
        assert len(results) == 5
        assert all(not r.scrape_ok for r in results)
        assert all(r.error_message is not None for r in results)

    @pytest.mark.asyncio
    async def test_list_page_fetch_failure_returns_empty(self) -> None:
        scraper = TauScraper()
        scraper.fetch_dynamic = AsyncMock(side_effect=ConnectionError("timeout"))

        results = await scraper.scrape()
        assert results == []

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(
        self, tau_list_html: str, tau_detail_html: str
    ) -> None:
        scraper = TauScraper()

        call_count = {"n": 0}

        async def _fetch_side_effect(url: str) -> str:
            if "undergraduate" in url:
                return tau_list_html
            call_count["n"] += 1
            if call_count["n"] % 2 == 0:
                raise ConnectionError("flaky")
            return tau_detail_html

        scraper.fetch_dynamic = AsyncMock(side_effect=_fetch_side_effect)

        results = await scraper.scrape()
        assert len(results) == 5
        ok = [r for r in results if r.scrape_ok]
        failed = [r for r in results if not r.scrape_ok]
        # 5 programs: calls 1,3,5 succeed; 2,4 fail
        assert len(ok) == 3
        assert len(failed) == 2

    @pytest.mark.asyncio
    async def test_first_result_is_computer_science(
        self, tau_list_html: str, tau_detail_html: str
    ) -> None:
        scraper = TauScraper()
        scraper.fetch_dynamic = AsyncMock(
            side_effect=[tau_list_html] + [tau_detail_html] * 5
        )

        results = await scraper.scrape()
        assert results[0].name_he == "מדעי המחשב"

    @pytest.mark.asyncio
    async def test_first_result_threshold(
        self, tau_list_html: str, tau_detail_html: str
    ) -> None:
        scraper = TauScraper()
        scraper.fetch_dynamic = AsyncMock(
            side_effect=[tau_list_html] + [tau_detail_html] * 5
        )

        results = await scraper.scrape()
        assert results[0].threshold_sekem == 730.0
