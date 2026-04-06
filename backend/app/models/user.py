import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.saved_program import SavedProgram


class User(Base):
    """
    Optional user account — anonymous use is the default.

    profile JSONB shape:
      {
        "bagrut_grades": [{"subject_code": str, "units": int, "grade": int}],
        "psychometric": int | null,
        "preferences": {"fields": [str], "cities": [str], "degree_types": [str]}
      }
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    # nullable — anonymous sessions have no email
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    # google | apple | email
    auth_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB(astext_type=Text()), nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    saved_programs: Mapped[list["SavedProgram"]] = relationship(
        "SavedProgram", back_populates="user", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!s} email={self.email!r}>"
