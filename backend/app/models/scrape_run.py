import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ScrapeStatus
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.institution import Institution


class ScrapeRun(Base):
    """Full audit trail of every scraper execution."""

    __tablename__ = "scrape_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[ScrapeStatus] = mapped_column(
        SAEnum(ScrapeStatus, name="scrape_status", create_type=False), nullable=False
    )
    records_updated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    anomaly_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    institution: Mapped["Institution"] = relationship(
        "Institution", back_populates="scrape_runs"
    )

    def __repr__(self) -> str:
        return (
            f"<ScrapeRun institution_id={self.institution_id!r} status={self.status.value!r}>"
        )
