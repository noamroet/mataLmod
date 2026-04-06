import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.career_data import CareerData
    from app.models.institution import Institution
    from app.models.saved_program import SavedProgram
    from app.models.sekem_formula import SekemFormula
    from app.models.syllabus import Syllabus


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    name_he: Mapped[str] = mapped_column(String(300), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Controlled vocabulary — see app.core.constants.FIELDS
    field: Mapped[str] = mapped_column(String(50), nullable=False)
    # BA / BSc / BEd / BArch / BFA / LLB
    degree_type: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    tuition_annual_ils: Mapped[int | None] = mapped_column(Integer, nullable=True)
    official_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    institution: Mapped["Institution"] = relationship(
        "Institution", back_populates="programs"
    )
    sekem_formulas: Mapped[list["SekemFormula"]] = relationship(
        "SekemFormula", back_populates="program", lazy="select"
    )
    syllabi: Mapped[list["Syllabus"]] = relationship(
        "Syllabus", back_populates="program", lazy="select"
    )
    career_data: Mapped[list["CareerData"]] = relationship(
        "CareerData", back_populates="program", lazy="select"
    )
    saved_programs: Mapped[list["SavedProgram"]] = relationship(
        "SavedProgram", back_populates="program", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Program id={self.id!s} name_he={self.name_he!r}>"
