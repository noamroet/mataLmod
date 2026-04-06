import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.program import Program
    from app.models.user import User


class RoadmapProgress(Base):
    """
    Persists which to-do items the user has checked off for a program roadmap.

    Unique on (user_id, program_id, item_index) — upserted on each sync.
    Written when the user logs in and localStorage is flushed to the server.
    """

    __tablename__ = "roadmap_progress"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "program_id", "item_index",
            name="uq_roadmap_progress_user_program_item",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    program: Mapped["Program"] = relationship("Program")

    def __repr__(self) -> str:
        return (
            f"<RoadmapProgress user={self.user_id!s} "
            f"program={self.program_id!s} item={self.item_index} "
            f"checked={self.checked}>"
        )
