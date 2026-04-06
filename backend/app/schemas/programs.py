"""
Response schemas for the /programs endpoints.

Hierarchy:
  ProgramBase          — shared column fields
  ProgramListItem      — ProgramBase + institution (for list endpoint)
  ProgramDetail        — ProgramBase + institution + formula + syllabus + career + freshness
  PaginatedPrograms    — wrapper for the paginated list response
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DemandTrend
from app.schemas.institutions import InstitutionResponse


class SekemFormulaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    year: int
    bagrut_weight: float
    psychometric_weight: float
    threshold_sekem: float
    subject_bonuses: list[Any] = Field(
        default_factory=list,
        description="list[{subject_code, units, bonus_points}]",
    )
    bagrut_requirements: list[Any] = Field(
        default_factory=list,
        description="list[{subject_code, min_units, min_grade, mandatory}]",
    )
    scraped_at: datetime
    source_url: str


class SyllabusResponse(BaseModel):
    """Syllabus summary — raw_html is intentionally excluded from the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    year_1_summary_he: str | None = None
    year_2_summary_he: str | None = None
    year_3_summary_he: str | None = None
    core_courses: list[Any] = Field(default_factory=list, description="list[str]")
    elective_tracks: list[Any] = Field(default_factory=list, description="list[str]")
    one_line_pitch_he: str | None = None
    summarized_at: datetime | None = None
    scraped_at: datetime


class CareerDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_titles: list[Any] = Field(default_factory=list, description="list[str]")
    avg_salary_min_ils: int | None = None
    avg_salary_max_ils: int | None = None
    demand_trend: DemandTrend
    data_year: int
    source: str
    updated_at: datetime


class DataFreshness(BaseModel):
    """Staleness indicator derived from the latest successful scrape run."""

    institution_id: str
    last_scrape_success: datetime | None = Field(
        default=None,
        description="Timestamp of the last successful scraper run for this institution.",
    )


class ProgramBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution_id: str
    name_he: str
    name_en: str | None = None
    field: str
    degree_type: str
    duration_years: int
    location: str
    tuition_annual_ils: int | None = None
    official_url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProgramListItem(ProgramBase):
    """Program with institution metadata — returned by the list endpoint."""

    institution: InstitutionResponse


class ProgramDetail(ProgramBase):
    """Full program detail — returned by the single-program endpoint."""

    institution: InstitutionResponse
    latest_sekem_formula: SekemFormulaResponse | None = None
    syllabus: SyllabusResponse | None = None
    career_data: CareerDataResponse | None = None
    data_freshness: DataFreshness


class PaginatedPrograms(BaseModel):
    items: list[ProgramListItem]
    total: int
    page: int
    limit: int
    pages: int = Field(description="Total number of pages at the current limit")
