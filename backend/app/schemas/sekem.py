"""
Pydantic v2 schemas for the Sekem calculation engine.

These are pure data-transfer objects — no SQLAlchemy dependency.
The ORM model lives in app.models.sekem_formula.
"""

import uuid

from pydantic import BaseModel, Field


class BagrutGrade(BaseModel):
    """One matriculation subject result from the Israeli bagrut exam."""

    subject_code: str
    units: int = Field(ge=1, le=5, description="Study units (1–5)")
    grade: int = Field(ge=0, le=100)


class SubjectBonus(BaseModel):
    """
    Mirrors the JSONB element shape in sekem_formulas.subject_bonuses.

    A user earns the bonus if they have *subject_code* at >= *units* in
    their bagrut profile.
    """

    subject_code: str
    units: int = Field(ge=1, le=5, description="Minimum units required to earn the bonus")
    bonus_points: float


class BagrutRequirement(BaseModel):
    """Mirrors the JSONB element shape in sekem_formulas.bagrut_requirements."""

    subject_code: str
    min_units: int
    min_grade: int
    mandatory: bool


class UserProfile(BaseModel):
    """The user's academic credentials needed for sekem calculation."""

    bagrut_grades: list[BagrutGrade]
    psychometric: int | None = Field(
        default=None,
        ge=200,
        le=800,
        description="Psychometric exam score; None if not taken or program is bagrut-only.",
    )


class SekemFormula(BaseModel):
    """
    Pydantic projection of a sekem_formulas DB row.
    Contains exactly the fields needed for calculation.
    """

    program_id: uuid.UUID
    bagrut_weight: float
    psychometric_weight: float
    threshold_sekem: float
    subject_bonuses: list[SubjectBonus] = Field(default_factory=list)
    bagrut_requirements: list[BagrutRequirement] = Field(default_factory=list)


class SekemResult(BaseModel):
    """Calculation output for one (profile, formula) pair."""

    sekem: float
    threshold: float
    margin: float = Field(description="sekem − threshold; positive means above threshold")
    eligible: bool = Field(description="sekem >= threshold")
    borderline: bool = Field(description="(threshold − 30) <= sekem < threshold")


class RankedProgram(BaseModel):
    """One entry in a ranked list returned by rank_programs()."""

    program_id: uuid.UUID
    sekem_result: SekemResult
    rank: int = Field(ge=1, description="1-indexed; 1 = best match for the user")
