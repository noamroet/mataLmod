"""Tests for GET /api/v1/programs and GET /api/v1/programs/{id}."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core import cache as cache_module
from tests.conftest import (
    PROGRAM_ID,
    make_career_data,
    make_institution,
    make_program,
    make_scrape_run,
    make_sekem_formula,
    make_syllabus,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _program_with_institution(**kw):
    """Return a program mock that has its institution attribute set."""
    inst = make_institution()
    prog = make_program(**kw)
    prog.institution = inst
    return prog


def _set_list_side_effect(mock_session, programs: list, total: int):
    """
    Configure mock for the two execute() calls in list_programs:
      1st call → count query  (scalar_one() = total)
      2nd call → paginated list  (scalars().unique().all() = programs)
    """
    count_mock = MagicMock()
    count_mock.scalar_one.return_value = total

    list_mock = MagicMock()
    list_mock.scalars.return_value.unique.return_value.all.return_value = programs

    mock_session.execute.side_effect = [count_mock, list_mock]


# ── List endpoint ─────────────────────────────────────────────────────────────

class TestListPrograms:
    async def test_returns_200_paginated(self, client, mock_session):
        prog = _program_with_institution()
        _set_list_side_effect(mock_session, [prog], total=1)

        response = await client.get("/api/v1/programs")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["page"] == 1
        assert body["limit"] == 20
        assert len(body["items"]) == 1

    async def test_response_item_shape(self, client, mock_session):
        prog = _program_with_institution()
        _set_list_side_effect(mock_session, [prog], total=1)

        item = (await client.get("/api/v1/programs")).json()["items"][0]

        assert item["id"] == str(PROGRAM_ID)
        assert item["name_he"] == "מדעי המחשב"
        assert item["field"] == "computer_science"
        assert item["degree_type"] == "BSc"
        assert item["institution"]["id"] == "TAU"

    async def test_empty_results(self, client, mock_session):
        _set_list_side_effect(mock_session, [], total=0)

        body = (await client.get("/api/v1/programs")).json()

        assert body["total"] == 0
        assert body["items"] == []
        assert body["pages"] == 0

    async def test_pagination_params_forwarded(self, client, mock_session):
        prog = _program_with_institution()
        _set_list_side_effect(mock_session, [prog], total=5)

        body = (await client.get("/api/v1/programs?page=2&limit=3")).json()

        assert body["page"] == 2
        assert body["limit"] == 3
        assert body["pages"] == 2  # ceil(5/3)

    async def test_filter_params_accepted(self, client, mock_session):
        prog = _program_with_institution(field="law", degree_type="LLB")
        _set_list_side_effect(mock_session, [prog], total=1)

        response = await client.get(
            "/api/v1/programs",
            params={"field": "law", "institution_id": "TAU", "degree_type": "LLB"},
        )

        assert response.status_code == 200
        assert response.json()["items"][0]["field"] == "law"

    async def test_pages_calculated_correctly(self, client, mock_session):
        progs = [_program_with_institution() for _ in range(3)]
        _set_list_side_effect(mock_session, progs, total=100)

        body = (await client.get("/api/v1/programs?limit=10")).json()
        assert body["pages"] == 10  # 100 / 10

    # ── Caching ───────────────────────────────────────────────────────────────

    async def test_cache_miss_calls_db_and_sets_cache(self, client, mock_session, monkeypatch):
        mock_set = AsyncMock()
        monkeypatch.setattr(cache_module, "cache_set", mock_set)

        prog = _program_with_institution()
        _set_list_side_effect(mock_session, [prog], total=1)

        await client.get("/api/v1/programs")

        mock_set.assert_awaited_once()
        assert mock_session.execute.call_count == 2  # count + list

    async def test_cache_hit_skips_db(self, client, mock_session, monkeypatch):
        cached = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 20,
            "pages": 0,
        }
        monkeypatch.setattr(cache_module, "cache_get", AsyncMock(return_value=cached))

        response = await client.get("/api/v1/programs")

        assert response.status_code == 200
        mock_session.execute.assert_not_called()

    async def test_different_filter_params_use_different_cache_keys(
        self, client, mock_session, monkeypatch
    ):
        """Verify that the cache key captures filter parameters."""
        seen_keys: list[str] = []

        async def _capture_get(key: str):
            seen_keys.append(key)
            return None  # always miss

        monkeypatch.setattr(cache_module, "cache_get", _capture_get)

        p1 = _program_with_institution(field="law")
        p2 = _program_with_institution(field="business")
        mock_session.execute.side_effect = [
            *(MagicMock(scalar_one=MagicMock(return_value=1)) for _ in range(2)),
            *(
                MagicMock(
                    **{
                        "scalars.return_value.unique.return_value.all.return_value": [p]
                    }
                )
                for p in [p1, p2]
            ),
        ]

        await client.get("/api/v1/programs?field=law")
        await client.get("/api/v1/programs?field=business")

        assert seen_keys[0] != seen_keys[1]
        assert "f=law" in seen_keys[0]
        assert "f=business" in seen_keys[1]


# ── Detail endpoint ───────────────────────────────────────────────────────────

class TestGetProgramDetail:
    def _set_detail_side_effect(
        self,
        mock_session,
        program=None,
        scrape_run=None,
    ):
        """
        Configure mock for the two execute() calls in get_program:
          1st call → program + associations (scalar_one_or_none)
          2nd call → latest scrape run (scalar_one_or_none)
        """
        prog_mock = MagicMock()
        prog_mock.scalar_one_or_none.return_value = program

        scrape_mock = MagicMock()
        scrape_mock.scalar_one_or_none.return_value = scrape_run

        mock_session.execute.side_effect = [prog_mock, scrape_mock]

    async def test_returns_200_with_full_detail(self, client, mock_session):
        formula = make_sekem_formula()
        syllabus = make_syllabus()
        career = make_career_data()
        prog = make_program(
            sekem_formulas=[formula],
            syllabi=[syllabus],
            career_data=[career],
            institution=make_institution(),
        )
        scrape_run = make_scrape_run()

        self._set_detail_side_effect(mock_session, program=prog, scrape_run=scrape_run)

        response = await client.get(f"/api/v1/programs/{PROGRAM_ID}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(PROGRAM_ID)
        assert body["name_he"] == "מדעי המחשב"

    async def test_response_includes_institution(self, client, mock_session):
        prog = make_program(institution=make_institution(), sekem_formulas=[], syllabi=[], career_data=[])
        self._set_detail_side_effect(mock_session, program=prog, scrape_run=None)

        body = (await client.get(f"/api/v1/programs/{PROGRAM_ID}")).json()
        assert body["institution"]["id"] == "TAU"
        assert body["institution"]["name_en"] == "Tel Aviv University"

    async def test_response_includes_latest_sekem_formula(self, client, mock_session):
        formula = make_sekem_formula(year=2025)
        prog = make_program(institution=make_institution(), sekem_formulas=[formula], syllabi=[], career_data=[])
        self._set_detail_side_effect(mock_session, program=prog, scrape_run=None)

        body = (await client.get(f"/api/v1/programs/{PROGRAM_ID}")).json()
        assert body["latest_sekem_formula"]["year"] == 2025
        assert body["latest_sekem_formula"]["threshold_sekem"] == 680.0

    async def test_latest_formula_is_highest_year(self, client, mock_session):
        """When multiple formulas exist, the highest year is selected."""
        f2024 = make_sekem_formula(year=2024, threshold_sekem=670.0)
        f2025 = make_sekem_formula(year=2025, threshold_sekem=680.0)
        prog = make_program(institution=make_institution(), sekem_formulas=[f2024, f2025], syllabi=[], career_data=[])
        self._set_detail_side_effect(mock_session, program=prog, scrape_run=None)

        body = (await client.get(f"/api/v1/programs/{PROGRAM_ID}")).json()
        assert body["latest_sekem_formula"]["year"] == 2025
        assert body["latest_sekem_formula"]["threshold_sekem"] == 680.0

    async def test_response_includes_syllabus(self, client, mock_session):
        syllabus = make_syllabus()
        prog = make_program(institution=make_institution(), sekem_formulas=[], syllabi=[syllabus], career_data=[])
        self._set_detail_side_effect(mock_session, program=prog, scrape_run=None)

        body = (await client.get(f"/api/v1/programs/{PROGRAM_ID}")).json()
        assert body["syllabus"]["year_1_summary_he"] == "שנה ראשונה — בסיסי מדעי המחשב"
        assert body["syllabus"]["core_courses"] == ["מבנה נתונים", "אלגוריתמים"]

    async def test_response_includes_career_data(self, client, mock_session):
        career = make_career_data()
        prog = make_program(institution=make_institution(), sekem_formulas=[], syllabi=[], career_data=[career])
        self._set_detail_side_effect(mock_session, program=prog, scrape_run=None)

        body = (await client.get(f"/api/v1/programs/{PROGRAM_ID}")).json()
        assert body["career_data"]["demand_trend"] == "growing"
        assert body["career_data"]["avg_salary_min_ils"] == 18_000

    async def test_null_fields_when_no_related_data(self, client, mock_session):
        """Programs with no formula/syllabus/career data should return nulls."""
        prog = make_program(institution=make_institution(), sekem_formulas=[], syllabi=[], career_data=[])
        self._set_detail_side_effect(mock_session, program=prog, scrape_run=None)

        body = (await client.get(f"/api/v1/programs/{PROGRAM_ID}")).json()
        assert body["latest_sekem_formula"] is None
        assert body["syllabus"] is None
        assert body["career_data"] is None

    async def test_data_freshness_with_scrape_run(self, client, mock_session):
        prog = make_program(institution=make_institution(), sekem_formulas=[], syllabi=[], career_data=[])
        scrape_run = make_scrape_run()
        self._set_detail_side_effect(mock_session, program=prog, scrape_run=scrape_run)

        body = (await client.get(f"/api/v1/programs/{PROGRAM_ID}")).json()
        assert body["data_freshness"]["institution_id"] == "TAU"
        assert body["data_freshness"]["last_scrape_success"] is not None

    async def test_data_freshness_null_when_no_scrape_run(self, client, mock_session):
        prog = make_program(institution=make_institution(), sekem_formulas=[], syllabi=[], career_data=[])
        self._set_detail_side_effect(mock_session, program=prog, scrape_run=None)

        body = (await client.get(f"/api/v1/programs/{PROGRAM_ID}")).json()
        assert body["data_freshness"]["last_scrape_success"] is None

    async def test_404_when_program_not_found(self, client, mock_session):
        prog_mock = MagicMock()
        prog_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = prog_mock

        response = await client.get(f"/api/v1/programs/{uuid.uuid4()}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_invalid_uuid_returns_422(self, client, mock_session):
        response = await client.get("/api/v1/programs/not-a-uuid")
        assert response.status_code == 422
