"""Tests for POST /api/v1/eligibility/calculate."""

import uuid
from unittest.mock import MagicMock

import pytest

from tests.conftest import (
    INST_ID,
    PROGRAM_ID,
    make_institution,
    make_program,
    make_sekem_formula,
)

_URL = "/api/v1/eligibility/calculate"

# ── Shared request bodies ─────────────────────────────────────────────────────

_STRONG_PROFILE = {
    "bagrut_grades": [
        {"subject_code": "math", "units": 5, "grade": 95},
        {"subject_code": "english", "units": 5, "grade": 88},
        {"subject_code": "physics", "units": 5, "grade": 90},
        {"subject_code": "hebrew", "units": 3, "grade": 85},
    ],
    "psychometric": 730,
}

_WEAK_PROFILE = {
    "bagrut_grades": [
        {"subject_code": "history", "units": 3, "grade": 60},
    ],
    "psychometric": 450,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _db_row(formula=None, program=None, institution=None):
    """Return a single (formula, program, institution) tuple for mock DB results."""
    f = formula or make_sekem_formula()
    p = program or make_program()
    i = institution or make_institution()
    return (f, p, i)


def _set_execute(mock_session, rows: list):
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    mock_session.execute.return_value = mock_result


# ── Success cases ─────────────────────────────────────────────────────────────

class TestCalculateEligibility:
    async def test_returns_200(self, client, mock_session):
        _set_execute(mock_session, [_db_row()])
        response = await client.post(_URL, json=_STRONG_PROFILE)
        assert response.status_code == 200

    async def test_response_structure(self, client, mock_session):
        _set_execute(mock_session, [_db_row()])
        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        assert "results" in body
        assert "total" in body
        assert "profile_summary" in body

    async def test_result_item_shape(self, client, mock_session):
        _set_execute(mock_session, [_db_row()])
        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        item = body["results"][0]
        assert "rank" in item
        assert "program" in item
        assert "sekem" in item
        assert "threshold" in item
        assert "margin" in item
        assert "eligible" in item
        assert "borderline" in item

    async def test_program_metadata_in_result(self, client, mock_session):
        formula = make_sekem_formula(program_id=PROGRAM_ID)
        program = make_program(id=PROGRAM_ID)
        institution = make_institution()
        _set_execute(mock_session, [_db_row(formula, program, institution)])

        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        prog = body["results"][0]["program"]
        assert prog["id"] == str(PROGRAM_ID)
        assert prog["name_he"] == "מדעי המחשב"
        assert prog["institution"]["id"] == INST_ID

    async def test_total_matches_all_programs(self, client, mock_session):
        """total should count all matched programs, not just the capped 50."""
        rows = [_db_row(make_sekem_formula(program_id=uuid.uuid4()), make_program(id=uuid.uuid4())) for _ in range(3)]
        _set_execute(mock_session, rows)

        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        assert body["total"] == 3

    async def test_empty_db_returns_empty_results(self, client, mock_session):
        _set_execute(mock_session, [])
        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        assert body["results"] == []
        assert body["total"] == 0

    async def test_results_capped_at_50(self, client, mock_session):
        """When DB has >50 programs, only top 50 are returned."""
        rows = []
        for i in range(60):
            pid = uuid.uuid4()
            rows.append(_db_row(make_sekem_formula(program_id=pid), make_program(id=pid)))
        _set_execute(mock_session, rows)

        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        assert len(body["results"]) == 50
        assert body["total"] == 60

    async def test_rank_numbers_start_at_1_and_are_sequential(self, client, mock_session):
        rows = []
        for i in range(3):
            pid = uuid.uuid4()
            rows.append(_db_row(make_sekem_formula(program_id=pid), make_program(id=pid)))
        _set_execute(mock_session, rows)

        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        ranks = [r["rank"] for r in body["results"]]
        assert ranks == [1, 2, 3]

    # ── Eligibility flags ─────────────────────────────────────────────────────

    async def test_eligible_program_flagged_correctly(self, client, mock_session):
        """Strong profile (sekem ≈ 725) against threshold 680 → eligible."""
        # formula: bagrut_weight=4.0, psychometric_weight=0.5, threshold=680
        formula = make_sekem_formula(threshold_sekem=680.0)
        _set_execute(mock_session, [_db_row(formula)])

        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        result = body["results"][0]
        assert result["eligible"] is True
        assert result["borderline"] is False
        assert result["margin"] > 0

    async def test_borderline_program_flagged_correctly(self, client, mock_session):
        """
        Weak profile: bagrut_avg ≈ 60, psychometric 450
        sekem = 60 × 4.0 + 450 × 0.5 = 240 + 225 = 465
        threshold = 480 → margin = -15 → borderline (within 30 gap)
        """
        formula = make_sekem_formula(threshold_sekem=480.0)
        _set_execute(mock_session, [_db_row(formula)])

        body = (await client.post(_URL, json=_WEAK_PROFILE)).json()
        result = body["results"][0]
        assert result["eligible"] is False
        assert result["borderline"] is True

    async def test_ineligible_program_flagged_correctly(self, client, mock_session):
        """
        Weak profile: sekem = 465, threshold 700 → margin = -235 → ineligible
        """
        formula = make_sekem_formula(threshold_sekem=700.0)
        _set_execute(mock_session, [_db_row(formula)])

        body = (await client.post(_URL, json=_WEAK_PROFILE)).json()
        result = body["results"][0]
        assert result["eligible"] is False
        assert result["borderline"] is False

    async def test_eligible_programs_ranked_before_borderline(self, client, mock_session):
        pid_elig = uuid.uuid4()
        pid_bord = uuid.uuid4()
        # Strong profile sekem ≈ 725
        elig_formula = make_sekem_formula(program_id=pid_elig, threshold_sekem=680.0)  # eligible
        bord_formula = make_sekem_formula(program_id=pid_bord, threshold_sekem=750.0)  # borderline (725 > 720)

        _set_execute(mock_session, [
            _db_row(bord_formula, make_program(id=pid_bord)),  # deliberately first in DB
            _db_row(elig_formula, make_program(id=pid_elig)),
        ])

        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        results = body["results"]
        # Eligible program must appear before borderline
        assert results[0]["eligible"] is True

    # ── Profile summary ───────────────────────────────────────────────────────

    async def test_profile_summary_bagrut_average(self, client, mock_session):
        """Profile summary reflects weighted bagrut average."""
        _set_execute(mock_session, [])
        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        summary = body["profile_summary"]
        # bagrut_avg for the strong profile ≈ 90.17 (see sekem service tests)
        assert 89.0 < summary["bagrut_average"] < 92.0

    async def test_profile_summary_psychometric(self, client, mock_session):
        _set_execute(mock_session, [])
        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        assert body["profile_summary"]["psychometric"] == 730

    async def test_profile_summary_subject_count(self, client, mock_session):
        _set_execute(mock_session, [])
        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        assert body["profile_summary"]["subject_count"] == 4

    async def test_profile_summary_has_five_unit_math_true(self, client, mock_session):
        _set_execute(mock_session, [])
        body = (await client.post(_URL, json=_STRONG_PROFILE)).json()
        assert body["profile_summary"]["has_five_unit_math"] is True

    async def test_profile_summary_has_five_unit_math_false(self, client, mock_session):
        profile_no_math = {
            "bagrut_grades": [{"subject_code": "english", "units": 5, "grade": 90}],
            "psychometric": 700,
        }
        _set_execute(mock_session, [])
        body = (await client.post(_URL, json=profile_no_math)).json()
        assert body["profile_summary"]["has_five_unit_math"] is False

    async def test_profile_summary_psychometric_none(self, client, mock_session):
        profile_no_psycho = {
            "bagrut_grades": [{"subject_code": "math", "units": 5, "grade": 90}],
        }
        _set_execute(mock_session, [])
        body = (await client.post(_URL, json=profile_no_psycho)).json()
        assert body["profile_summary"]["psychometric"] is None

    # ── Preferences filtering ─────────────────────────────────────────────────

    async def test_preferences_field_filter_accepted(self, client, mock_session):
        formula = make_sekem_formula()
        prog = make_program(field="computer_science")
        _set_execute(mock_session, [_db_row(formula, prog)])

        body = (await client.post(_URL, json={
            **_STRONG_PROFILE,
            "preferences": {"fields": ["computer_science"]},
        })).json()

        response_item = body["results"][0]
        assert response_item["program"]["field"] == "computer_science"

    async def test_preferences_empty_when_no_match(self, client, mock_session):
        _set_execute(mock_session, [])  # DB returns nothing after filter
        body = (await client.post(_URL, json={
            **_STRONG_PROFILE,
            "preferences": {"fields": ["medicine"], "institution_ids": ["HUJI"]},
        })).json()
        assert body["results"] == []
        assert body["total"] == 0

    # ── Validation ────────────────────────────────────────────────────────────

    async def test_missing_bagrut_grades_returns_422(self, client, mock_session):
        response = await client.post(_URL, json={"psychometric": 700})
        assert response.status_code == 422

    async def test_invalid_psychometric_range_returns_422(self, client, mock_session):
        body = {
            "bagrut_grades": [{"subject_code": "math", "units": 5, "grade": 90}],
            "psychometric": 900,  # max is 800
        }
        response = await client.post(_URL, json=body)
        assert response.status_code == 422

    async def test_invalid_grade_range_returns_422(self, client, mock_session):
        body = {
            "bagrut_grades": [{"subject_code": "math", "units": 5, "grade": 110}],  # max 100
        }
        response = await client.post(_URL, json=body)
        assert response.status_code == 422

    async def test_empty_bagrut_grades_returns_200(self, client, mock_session):
        """Empty grade list is valid — user may not have bagrut yet."""
        _set_execute(mock_session, [])
        response = await client.post(_URL, json={"bagrut_grades": []})
        assert response.status_code == 200
