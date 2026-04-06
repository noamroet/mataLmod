import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.program import Program


class SekemFormula(Base):
    """
    Admission formula for a program in a given academic year.

    Rows are NEVER deleted — only appended.
    Always query WHERE year = (SELECT MAX(year) FROM sekem_formulas WHERE program_id = ...).
    """

    __tablename__ = "sekem_formulas"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Academic year, e.g. 2025
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    bagrut_weight: Mapped[float] = mapped_column(Float, nullable=False)
    psychometric_weight: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_sekem: Mapped[float] = mapped_column(Float, nullable=False)
    # list[{subject_code: str, units: int, bonus_points: float}]
    subject_bonuses: Mapped[list[Any]] = mapped_column(
        JSONB(astext_type=Text()), nullable=False, server_default="[]"
    )
    # list[{subject_code: str, min_units: int, min_grade: int, mandatory: bool}]
    bagrut_requirements: Mapped[list[Any]] = mapped_column(
        JSONB(astext_type=Text()), nullable=False, server_default="[]"
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="sekem_formulas")

    def __repr__(self) -> str:
        return f"<SekemFormula program_id={self.program_id!s} year={self.year}>"
