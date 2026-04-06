"""
Tests for app/services/sekem.py — 100% coverage target.

Pre-computed reference values (derived with exact fractions):
  avg_A   = 3220/37  ≈ 87.0270  (5-unit math 100 + 3-unit history 60)
  tau_avg = 2615/29  ≈ 90.1724  (TAU CS profile, see fixture)
  tau_sekem          ≈ 725.6897 (tau_avg × 4.0 + 730 × 0.5)
"""

import uuid

import pytest

from app.schemas.sekem import BagrutGrade, SekemFormula, SubjectBonus, UserProfile
from app.services.sekem import (
    calculate_sekem,
    rank_programs,
    weighted_bagrut_average,
)

# ── Reusable formula fixtures ─────────────────────────────────────────────────

PROGRAM_A = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
PROGRAM_B = uuid.UUID("00000000-0000-0000-0000-0000000000bb")
PROGRAM_C = uuid.UUID("00000000-0000-0000-0000-0000000000cc")
PROGRAM_D = uuid.UUID("00000000-0000-0000-0000-0000000000dd")

# Shared formula parameters used across several tests
_BASE_FORMULA_KWARGS = dict(
    bagrut_weight=4.0,
    psychometric_weight=0.5,
    threshold_sekem=680.0,
)


def _formula(**overrides) -> SekemFormula:
    return SekemFormula(program_id=PROGRAM_A, **{**_BASE_FORMULA_KWARGS, **overrides})


# ── weighted_bagrut_average ───────────────────────────────────────────────────


class TestWeightedBagrutAverage:
    def test_empty_grades_returns_zero(self) -> None:
        assert weighted_bagrut_average([]) == 0.0

    def test_single_non_five_unit_subject(self) -> None:
        grades = [BagrutGrade(subject_code="history", units=3, grade=80)]
        # Effective weight = 3 × 1.0; weighted grade = 240; avg = 80.0
        assert weighted_bagrut_average(grades) == pytest.approx(80.0)

    def test_single_five_unit_subject(self) -> None:
        # 5-unit grade equals itself (single subject → average equals grade)
        grades = [BagrutGrade(subject_code="math", units=5, grade=92)]
        assert weighted_bagrut_average(grades) == pytest.approx(92.0)

    def test_five_unit_bonus_inflates_average(self) -> None:
        """
        5-unit math 100 + 3-unit history 60.

        Without bonus: (5×100 + 3×60) / (5+3) = 680/8 = 85.0
        With    bonus: (6.25×100 + 3×60) / (6.25+3) = 805/9.25 ≈ 87.027
        """
        grades = [
            BagrutGrade(subject_code="math", units=5, grade=100),
            BagrutGrade(subject_code="history", units=3, grade=60),
        ]
        result = weighted_bagrut_average(grades)
        assert result == pytest.approx(3220 / 37, rel=1e-9)  # 3220/37 ≈ 87.027
        # Confirm the 5-unit bonus raised the average above the naive average
        assert result > 85.0

    def test_all_five_unit_same_grade_unchanged(self) -> None:
        """Bonus cancels out when every subject is 5-unit at the same grade."""
        grades = [
            BagrutGrade(subject_code="math", units=5, grade=90),
            BagrutGrade(subject_code="english", units=5, grade=90),
            BagrutGrade(subject_code="physics", units=5, grade=90),
        ]
        assert weighted_bagrut_average(grades) == pytest.approx(90.0)

    def test_mixed_units_weighted_correctly(self) -> None:
        """1-unit subject should contribute very little to the average."""
        grades = [
            BagrutGrade(subject_code="art", units=1, grade=50),
            BagrutGrade(subject_code="math", units=5, grade=100),
        ]
        result = weighted_bagrut_average(grades)
        # art: 1×50=50; math: 6.25×100=625; total_w=7.25; avg=675/7.25≈93.10
        assert result == pytest.approx(675 / 7.25, rel=1e-9)
        assert result > 90  # math dominates


# ── calculate_sekem ───────────────────────────────────────────────────────────


@pytest.fixture()
def tau_cs_formula() -> SekemFormula:
    """TAU Computer Science admission formula (representative 2025 weights)."""
    # _formula() already injects program_id=PROGRAM_A and the base kwargs;
    # no need to repeat them here.
    return _formula()


@pytest.fixture()
def tau_cs_profile() -> UserProfile:
    """Strong student profile — above TAU CS threshold."""
    return UserProfile(
        bagrut_grades=[
            BagrutGrade(subject_code="math", units=5, grade=95),
            BagrutGrade(subject_code="english", units=5, grade=88),
            BagrutGrade(subject_code="physics", units=5, grade=90),
            BagrutGrade(subject_code="hebrew", units=3, grade=85),
        ],
        psychometric=730,
    )


class TestCalculateSekemTauCS:
    """Known-value test against TAU Computer Science formula."""

    def test_sekem_value(self, tau_cs_formula, tau_cs_profile) -> None:
        """
        Exact expected value (derived with exact fractions):
          bagrut_avg  = 2615/29 ≈ 90.1724
          sekem       = (2615/29) × 4 + 730 × 0.5 = 21045/29 ≈ 725.6897
        """
        result = calculate_sekem(tau_cs_profile, tau_cs_formula)
        assert result.sekem == pytest.approx(21045 / 29, rel=1e-4)

    def test_eligible(self, tau_cs_formula, tau_cs_profile) -> None:
        result = calculate_sekem(tau_cs_profile, tau_cs_formula)
        assert result.eligible is True
        assert result.borderline is False

    def test_margin_is_positive(self, tau_cs_formula, tau_cs_profile) -> None:
        result = calculate_sekem(tau_cs_profile, tau_cs_formula)
        # sekem ≈ 725.69, threshold = 680 → margin ≈ 45.69
        assert result.margin == pytest.approx(21045 / 29 - 680, rel=1e-4)
        assert result.margin > 0

    def test_threshold_recorded_correctly(self, tau_cs_formula, tau_cs_profile) -> None:
        result = calculate_sekem(tau_cs_profile, tau_cs_formula)
        assert result.threshold == 680.0


# ── Subject bonuses ───────────────────────────────────────────────────────────


class TestSubjectBonuses:
    """Tests for the bonus qualification logic."""

    def _formula_with_bonus(self, bonus: SubjectBonus) -> SekemFormula:
        return SekemFormula(
            program_id=PROGRAM_A,
            **_BASE_FORMULA_KWARGS,
            subject_bonuses=[bonus],
        )

    def test_bonus_added_when_user_qualifies(self) -> None:
        """User has 5-unit math → earns the 5-unit-math bonus of +10."""
        bonus = SubjectBonus(subject_code="math", units=5, bonus_points=10.0)
        formula = self._formula_with_bonus(bonus)
        profile = UserProfile(
            bagrut_grades=[BagrutGrade(subject_code="math", units=5, grade=90)],
            psychometric=700,
        )
        # Base sekem = 90 × 4.0 + 700 × 0.5 = 360 + 350 = 710
        # With bonus = 720
        result = calculate_sekem(profile, formula)
        assert result.sekem == pytest.approx(720.0)
        assert result.eligible is True

    def test_bonus_added_when_user_has_more_units(self) -> None:
        """Bonus requires 3-unit; user has 5-unit → still qualifies (>=)."""
        bonus = SubjectBonus(subject_code="english", units=3, bonus_points=5.0)
        formula = self._formula_with_bonus(bonus)
        profile = UserProfile(
            bagrut_grades=[BagrutGrade(subject_code="english", units=5, grade=80)],
            psychometric=700,
        )
        # bagrut_avg = 80 (single subject → avg equals grade)
        # sekem = 80 × 4.0 + 700 × 0.5 = 320 + 350 = 670 + 5 = 675
        result = calculate_sekem(profile, formula)
        assert result.sekem == pytest.approx(675.0)

    def test_bonus_not_added_when_units_insufficient(self) -> None:
        """Bonus requires 5-unit math; user only has 3-unit → no bonus."""
        bonus = SubjectBonus(subject_code="math", units=5, bonus_points=10.0)
        formula = self._formula_with_bonus(bonus)
        profile = UserProfile(
            bagrut_grades=[BagrutGrade(subject_code="math", units=3, grade=90)],
            psychometric=700,
        )
        # sekem = 90 × 4.0 + 700 × 0.5 = 360 + 350 = 710  (no bonus)
        result = calculate_sekem(profile, formula)
        assert result.sekem == pytest.approx(710.0)

    def test_bonus_not_added_when_subject_missing(self) -> None:
        """Bonus is for math; user has no math in their grades → no bonus."""
        bonus = SubjectBonus(subject_code="math", units=5, bonus_points=10.0)
        formula = self._formula_with_bonus(bonus)
        profile = UserProfile(
            bagrut_grades=[BagrutGrade(subject_code="history", units=5, grade=85)],
            psychometric=700,
        )
        # sekem = 85 × 4.0 + 700 × 0.5 = 340 + 350 = 690  (no bonus)
        result = calculate_sekem(profile, formula)
        assert result.sekem == pytest.approx(690.0)

    def test_multiple_bonuses_stacked(self) -> None:
        """User qualifies for two bonuses; both are added."""
        formula = SekemFormula(
            program_id=PROGRAM_A,
            **_BASE_FORMULA_KWARGS,
            subject_bonuses=[
                SubjectBonus(subject_code="math", units=5, bonus_points=10.0),
                SubjectBonus(subject_code="physics", units=5, bonus_points=5.0),
            ],
        )
        profile = UserProfile(
            bagrut_grades=[
                BagrutGrade(subject_code="math", units=5, grade=90),
                BagrutGrade(subject_code="physics", units=5, grade=90),
            ],
            psychometric=700,
        )
        # bagrut_avg = 90 (two equal 5-unit subjects)
        # sekem = 90 × 4.0 + 700 × 0.5 = 360 + 350 = 710 + 15 = 725
        result = calculate_sekem(profile, formula)
        assert result.sekem == pytest.approx(725.0)


# ── Borderline detection ──────────────────────────────────────────────────────


class TestBorderlineDetection:
    """
    Borderline window: threshold − 30 <= sekem < threshold.

    All tests use formula with threshold=680 and a single 3-unit subject
    so bagrut_avg equals the grade exactly (no 5-unit multiplier).
    """

    def _simple_profile(self, grade: int, psychometric: int) -> UserProfile:
        return UserProfile(
            bagrut_grades=[BagrutGrade(subject_code="math", units=3, grade=grade)],
            psychometric=psychometric,
        )

    def _sekem_for(self, grade: int, psychometric: int) -> float:
        # sekem = grade × 4.0 + psychometric × 0.5
        return grade * 4.0 + psychometric * 0.5

    def test_borderline_28_below_threshold(self) -> None:
        """sekem = 652 (28 below 680) → borderline."""
        # 80 × 4 + 664 × 0.5 = 320 + 332 = 652
        assert self._sekem_for(80, 664) == 652.0
        result = calculate_sekem(self._simple_profile(80, 664), _formula())
        assert result.sekem == pytest.approx(652.0)
        assert result.eligible is False
        assert result.borderline is True
        assert result.margin == pytest.approx(-28.0)

    def test_borderline_exactly_at_threshold_minus_30(self) -> None:
        """sekem = 650 (exactly 30 below threshold) → still borderline (>=)."""
        # 80 × 4 + 660 × 0.5 = 320 + 330 = 650
        assert self._sekem_for(80, 660) == 650.0
        result = calculate_sekem(self._simple_profile(80, 660), _formula())
        assert result.sekem == pytest.approx(650.0)
        assert result.borderline is True
        assert result.margin == pytest.approx(-30.0)

    def test_not_borderline_31_below_threshold(self) -> None:
        """sekem = 649 (31 below threshold) → ineligible, not borderline."""
        # 80 × 4 + 658 × 0.5 = 320 + 329 = 649
        assert self._sekem_for(80, 658) == 649.0
        result = calculate_sekem(self._simple_profile(80, 658), _formula())
        assert result.sekem == pytest.approx(649.0)
        assert result.eligible is False
        assert result.borderline is False

    def test_eligible_is_not_borderline(self) -> None:
        """Eligible programs must never be flagged borderline."""
        # sekem = 700 (above 680)
        # 80 × 4 + 700 × 0.5 = 320 + 350 = 670... need sekem > 680
        # 85 × 4 + 700 × 0.5 = 340 + 350 = 690
        result = calculate_sekem(self._simple_profile(85, 700), _formula())
        assert result.eligible is True
        assert result.borderline is False

    def test_ineligible_well_below_is_not_borderline(self) -> None:
        """sekem = 580 (100 below threshold) → ineligible and not borderline."""
        # 80 × 4 + 440 × 0.5 = 320 + 220 = 540... adjust
        # 60 × 4 + 680 × 0.5 = 240 + 340 = 580
        result = calculate_sekem(self._simple_profile(60, 680), _formula())
        assert result.sekem == pytest.approx(580.0)
        assert result.eligible is False
        assert result.borderline is False


# ── Psychometric = None ───────────────────────────────────────────────────────


class TestPsychometricNone:
    """Programs with psychometric_weight=0 only use the bagrut average."""

    def test_bagrut_only_program_eligible(self) -> None:
        """
        No psychometric exam → psychometric treated as 0.
        With weight=0 the score is entirely bagrut-driven.
        """
        formula = SekemFormula(
            program_id=PROGRAM_A,
            bagrut_weight=1.0,
            psychometric_weight=0.0,
            threshold_sekem=80.0,
        )
        profile = UserProfile(
            bagrut_grades=[BagrutGrade(subject_code="math", units=5, grade=90)],
            psychometric=None,
        )
        result = calculate_sekem(profile, formula)
        assert result.sekem == pytest.approx(90.0)
        assert result.eligible is True

    def test_bagrut_only_program_borderline(self) -> None:
        """Grade of 65 on a threshold-80 bagrut-only program → borderline."""
        formula = SekemFormula(
            program_id=PROGRAM_A,
            bagrut_weight=1.0,
            psychometric_weight=0.0,
            threshold_sekem=80.0,
        )
        profile = UserProfile(
            bagrut_grades=[BagrutGrade(subject_code="history", units=3, grade=65)],
            psychometric=None,
        )
        result = calculate_sekem(profile, formula)
        assert result.sekem == pytest.approx(65.0)
        assert result.eligible is False
        assert result.borderline is True  # 65 >= 80 − 30 = 50

    def test_psychometric_none_with_nonzero_weight_treated_as_zero(self) -> None:
        """
        If user has no psychometric but formula has nonzero psychometric_weight,
        the missing score is substituted with 0 (conservative approach).
        """
        formula = _formula()  # psychometric_weight = 0.5
        profile = UserProfile(
            bagrut_grades=[BagrutGrade(subject_code="math", units=3, grade=80)],
            psychometric=None,
        )
        # sekem = 80 × 4.0 + 0 × 0.5 = 320.0
        result = calculate_sekem(profile, formula)
        assert result.sekem == pytest.approx(320.0)
        assert result.eligible is False


# ── rank_programs ─────────────────────────────────────────────────────────────


class TestRankPrograms:
    """Tests for ranking order: eligible > borderline > ineligible."""

    @pytest.fixture()
    def profile(self) -> UserProfile:
        """Fixed profile that produces sekem=652 against threshold=680."""
        return UserProfile(
            bagrut_grades=[BagrutGrade(subject_code="math", units=3, grade=80)],
            psychometric=664,
        )

    def _formula_with_threshold(self, program_id: uuid.UUID, threshold: float) -> SekemFormula:
        return SekemFormula(
            program_id=program_id,
            bagrut_weight=4.0,
            psychometric_weight=0.5,
            threshold_sekem=threshold,
        )

    def test_ranking_order_all_categories(self, profile) -> None:
        """
        Profile sekem = 652 against these thresholds:
          A: threshold 600 → eligible,   margin +52
          B: threshold 640 → eligible,   margin +12
          C: threshold 680 → borderline, margin -28
          D: threshold 720 → ineligible, margin -68
        Expected rank: A=1, B=2, C=3, D=4
        """
        formulas = [
            self._formula_with_threshold(PROGRAM_D, 720.0),  # deliberately shuffled
            self._formula_with_threshold(PROGRAM_C, 680.0),
            self._formula_with_threshold(PROGRAM_A, 600.0),
            self._formula_with_threshold(PROGRAM_B, 640.0),
        ]
        ranked = rank_programs(profile, formulas)

        assert len(ranked) == 4
        assert [r.program_id for r in ranked] == [PROGRAM_A, PROGRAM_B, PROGRAM_C, PROGRAM_D]
        assert [r.rank for r in ranked] == [1, 2, 3, 4]

    def test_eligible_programs_sorted_by_margin_descending(self, profile) -> None:
        """Two eligible programs: higher margin must rank first."""
        formulas = [
            self._formula_with_threshold(PROGRAM_B, 640.0),  # margin +12
            self._formula_with_threshold(PROGRAM_A, 600.0),  # margin +52
        ]
        ranked = rank_programs(profile, formulas)
        assert ranked[0].program_id == PROGRAM_A  # larger margin first
        assert ranked[1].program_id == PROGRAM_B

    def test_borderline_programs_sorted_by_margin_descending(self, profile) -> None:
        """Two borderline programs: least deficit (margin closest to 0) ranks first."""
        # profile sekem = 652
        # PROGRAM_A threshold=662 → margin=-10 (less deficit, ranks first)
        # PROGRAM_B threshold=680 → margin=-28
        formulas = [
            self._formula_with_threshold(PROGRAM_B, 680.0),  # margin -28
            self._formula_with_threshold(PROGRAM_A, 662.0),  # margin -10
        ]
        ranked = rank_programs(profile, formulas)
        assert ranked[0].program_id == PROGRAM_A  # margin=-10 (less deficit)
        assert ranked[1].program_id == PROGRAM_B  # margin=-28

    def test_eligible_always_before_borderline(self, profile) -> None:
        formulas = [
            self._formula_with_threshold(PROGRAM_B, 680.0),  # borderline
            self._formula_with_threshold(PROGRAM_A, 600.0),  # eligible
        ]
        ranked = rank_programs(profile, formulas)
        assert ranked[0].sekem_result.eligible is True
        assert ranked[1].sekem_result.borderline is True

    def test_borderline_always_before_ineligible(self, profile) -> None:
        formulas = [
            self._formula_with_threshold(PROGRAM_B, 720.0),  # ineligible
            self._formula_with_threshold(PROGRAM_A, 680.0),  # borderline
        ]
        ranked = rank_programs(profile, formulas)
        assert ranked[0].sekem_result.borderline is True
        assert ranked[1].sekem_result.eligible is False
        assert ranked[1].sekem_result.borderline is False

    def test_empty_formulas_returns_empty_list(self) -> None:
        result = rank_programs(profile=UserProfile(bagrut_grades=[]), formulas=[])
        assert result == []

    def test_rank_numbers_are_sequential_from_one(self, profile) -> None:
        formulas = [
            self._formula_with_threshold(PROGRAM_A, 600.0),
            self._formula_with_threshold(PROGRAM_B, 680.0),
            self._formula_with_threshold(PROGRAM_C, 720.0),
        ]
        ranked = rank_programs(profile, formulas)
        assert [r.rank for r in ranked] == [1, 2, 3]

    def test_sekem_result_embedded_correctly(self, profile) -> None:
        """rank_programs must embed the full SekemResult in each RankedProgram."""
        formulas = [self._formula_with_threshold(PROGRAM_A, 600.0)]
        ranked = rank_programs(profile, formulas)
        r = ranked[0]
        assert r.program_id == PROGRAM_A
        assert r.sekem_result.eligible is True
        assert r.sekem_result.threshold == 600.0
