import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DemandTrend
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.program import Program


class CareerData(Base):
    __tablename__ = "career_data"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # list[str]
    job_titles: Mapped[list[Any]] = mapped_column(
        JSONB(astext_type=Text()), nullable=False, server_default="[]"
    )
    avg_salary_min_ils: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_salary_max_ils: Mapped[int | None] = mapped_column(Integer, nullable=True)
    demand_trend: Mapped[DemandTrend] = mapped_column(
        SAEnum(DemandTrend, name="demand_trend", create_type=False), nullable=False
    )
    data_year: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(300), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="career_data")

    def __repr__(self) -> str:
        return f"<CareerData program_id={self.program_id!s} year={self.data_year}>"
