"""
Sekem calculation engine.

Sekem (סקם) is the Israeli university admission composite score.
It is a weighted combination of the bagrut (matriculation) average
and the psychometric exam score, with optional per-subject bonuses.

Reference formula (from CLAUDE.md):
    bagrut_avg = weighted_average(grades, five_unit_bonus=1.25)
    sekem = (bagrut_avg * formula.bagrut_weight) + (psychometric * formula.psychometric_weight)
    for bonus in formula.subject_bonuses:
        if user_qualifies(profile, bonus):
            sekem += bonus.bonus_points
    eligible   = sekem >= threshold
    borderline = (threshold - 30) <= sekem < threshold
"""

from app.schemas.sekem import (
    BagrutGrade,
    RankedProgram,
    SekemFormula,
    SekemResult,
    SubjectBonus,
    UserProfile,
)

# 5-unit subjects receive a 25% effective-weight bonus
_FIVE_UNIT_MULTIPLIER: float = 1.25

# Gap below threshold that qualifies as "borderline"
_BORDERLINE_GAP: float = 30.0


def weighted_bagrut_average(grades: list[BagrutGrade]) -> float:
    """
    Return the weighted bagrut average (0–100 scale).

    Weighting rules:
    - Each subject contributes proportionally to its unit count.
    - 5-unit subjects are boosted: they count as ``units × 1.25`` units
      (i.e. as 6.25 units instead of 5), giving them a larger share of
      the overall average.

    Returns 0.0 for an empty grade list.
    """
    if not grades:
        return 0.0

    total_weight: float = 0.0
    total_weighted_grade: float = 0.0

    for g in grades:
        multiplier = _FIVE_UNIT_MULTIPLIER if g.units == 5 else 1.0
        effective_weight = g.units * multiplier
        total_weight += effective_weight
        total_weighted_grade += g.grade * effective_weight

    return total_weighted_grade / total_weight


def _qualifies_for_bonus(profile: UserProfile, bonus: SubjectBonus) -> bool:
    """
    Return True if the user earns *bonus*.

    The user qualifies when their bagrut profile contains an entry for
    ``bonus.subject_code`` with ``units >= bonus.units``.
    """
    return any(
        g.subject_code == bonus.subject_code and g.units >= bonus.units
        for g in profile.bagrut_grades
    )


def calculate_sekem(profile: UserProfile, formula: SekemFormula) -> SekemResult:
    """
    Calculate the sekem composite score for one (profile, formula) pair.

    ``profile.psychometric = None`` is treated as 0, which is correct for
    programs with ``formula.psychometric_weight == 0`` (bagrut-only admission).
    """
    bagrut_avg = weighted_bagrut_average(profile.bagrut_grades)
    psychometric = profile.psychometric if profile.psychometric is not None else 0

    # Bagrut average is on a 0–100 scale; psychometric is on a 200–800 scale.
    # Weights are stored as true multipliers (NOT percentages), chosen so that
    # each component contributes proportionally at maximum:
    #   50/50 split → bagrut_weight=4.0, psychometric_weight=0.5
    #   (max sekem = 100×4 + 800×0.5 = 800, matching the threshold scale)
    # Per-institution defaults:
    #   TAU / HUJI / BGU / BIU / Haifa / Ariel: 4.0 / 0.5
    #   Technion (engineering-heavy):             3.2 / 0.6
    sekem: float = (
        bagrut_avg * formula.bagrut_weight
        + psychometric * formula.psychometric_weight
    )

    for bonus in formula.subject_bonuses:
        if _qualifies_for_bonus(profile, bonus):
            sekem += bonus.bonus_points

    threshold = formula.threshold_sekem
    sekem_r = round(sekem, 4)
    margin = round(sekem_r - threshold, 4)
    eligible = sekem_r >= threshold
    borderline = not eligible and sekem_r >= (threshold - _BORDERLINE_GAP)

    return SekemResult(
        sekem=sekem_r,
        threshold=threshold,
        margin=margin,
        eligible=eligible,
        borderline=borderline,
    )


def rank_programs(
    profile: UserProfile,
    formulas: list[SekemFormula],
) -> list[RankedProgram]:
    """
    Rank all programs for a given user profile.

    Sort order:
      1. **Eligible** (``sekem >= threshold``) — highest margin first
      2. **Borderline** (within 30 points below threshold) — least deficit first
      3. **Ineligible** — least deficit first (closest to threshold)

    Returns a list of :class:`RankedProgram` with 1-indexed ``rank``.
    """
    scored: list[tuple[SekemFormula, SekemResult]] = [
        (f, calculate_sekem(profile, f)) for f in formulas
    ]

    def _sort_key(item: tuple[SekemFormula, SekemResult]) -> tuple[int, float]:
        _, r = item
        if r.eligible:
            return (0, -r.margin)  # category 0; descending margin
        if r.borderline:
            return (1, -r.margin)  # category 1; least deficit first
        return (2, -r.margin)      # category 2; least deficit first

    scored.sort(key=_sort_key)

    return [
        RankedProgram(program_id=f.program_id, sekem_result=r, rank=i)
        for i, (f, r) in enumerate(scored, start=1)
    ]
