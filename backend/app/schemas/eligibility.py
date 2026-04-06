"""
Request / response schemas for POST /api/v1/eligibility/calculate.
"""

from pydantic import BaseModel, Field

from app.schemas.programs import ProgramListItem
from app.schemas.sekem import BagrutGrade


class Preferences(BaseModel):
    """Optional filters applied before the sekem calculation."""

    fields: list[str] = Field(
        default_factory=list,
        description="Restrict results to these field codes (see constants.FIELDS).",
    )
    locations: list[str] = Field(
        default_factory=list,
        description="Restrict results to programs at these locations (Hebrew city names).",
    )
    degree_types: list[str] = Field(
        default_factory=list,
        description="Restrict results to these degree types (BA/BSc/BEd/BArch/BFA/LLB).",
    )
    institution_ids: list[str] = Field(
        default_factory=list,
        description="Restrict results to these institution IDs (e.g. 'TAU', 'HUJI').",
    )


class EligibilityRequest(BaseModel):
    bagrut_grades: list[BagrutGrade] = Field(
        description="All bagrut subjects the user studied."
    )
    psychometric: int | None = Field(
        default=None,
        ge=200,
        le=800,
        description="Psychometric exam score; omit if not yet taken.",
    )
    preferences: Preferences = Field(default_factory=Preferences)


class ProfileSummary(BaseModel):
    """Derived summary of the user profile — shown alongside results."""

    bagrut_average: float = Field(
        description="Weighted bagrut average (5-unit subjects boosted by ×1.25)."
    )
    psychometric: int | None
    subject_count: int
    has_five_unit_math: bool = Field(
        description="True if the profile includes 5-unit mathematics."
    )


class EligibilityResultItem(BaseModel):
    """One ranked program in the eligibility response."""

    rank: int = Field(ge=1)
    program: ProgramListItem
    sekem: float
    threshold: float
    margin: float = Field(description="sekem − threshold; positive means eligible.")
    eligible: bool
    borderline: bool


class EligibilityResponse(BaseModel):
    results: list[EligibilityResultItem] = Field(
        description="Top 50 programs ranked by eligibility and margin."
    )
    total: int = Field(
        description="Total number of programs matched (before the top-50 cap)."
    )
    profile_summary: ProfileSummary
