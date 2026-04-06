from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import InstitutionType
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.program import Program
    from app.models.scrape_run import ScrapeRun


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name_he: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[InstitutionType] = mapped_column(
        SAEnum(InstitutionType, name="institution_type", create_type=False),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    website_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    programs: Mapped[list["Program"]] = relationship(
        "Program", back_populates="institution", lazy="select"
    )
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(
        "ScrapeRun", back_populates="institution", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Institution id={self.id!r} name_en={self.name_en!r}>"
