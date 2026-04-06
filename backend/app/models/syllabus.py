import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.program import Program


class Syllabus(Base):
    __tablename__ = "syllabi"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    year_1_summary_he: Mapped[str | None] = mapped_column(Text, nullable=True)
    year_2_summary_he: Mapped[str | None] = mapped_column(Text, nullable=True)
    year_3_summary_he: Mapped[str | None] = mapped_column(Text, nullable=True)
    # list[str]
    core_courses: Mapped[list[Any]] = mapped_column(
        JSONB(astext_type=Text()), nullable=False, server_default="[]"
    )
    # list[str]
    elective_tracks: Mapped[list[Any]] = mapped_column(
        JSONB(astext_type=Text()), nullable=False, server_default="[]"
    )
    one_line_pitch_he: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_html: Mapped[str] = mapped_column(Text, nullable=False)
    summarized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="syllabi")

    def __repr__(self) -> str:
        return f"<Syllabus program_id={self.program_id!s}>"
