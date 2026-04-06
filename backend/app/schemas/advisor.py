"""
Request / response schemas for POST /api/v1/advisor/chat.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.sekem import BagrutGrade


class AdvisorMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class UserProfileCompact(BaseModel):
    """Compact user profile included in every advisor request."""

    bagrut_grades: list[BagrutGrade] = Field(default_factory=list)
    psychometric: int | None = Field(
        default=None,
        ge=200,
        le=800,
        description="Psychometric score; None if not yet taken.",
    )


class AdvisorChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="The user's latest message.",
    )
    user_profile: UserProfileCompact = Field(
        default_factory=UserProfileCompact,
        description="User's bagrut + psychometric data for personalised context.",
    )
    current_program_id: uuid.UUID | None = Field(
        default=None,
        description="ID of the program page the user is currently viewing, if any.",
    )
    conversation_history: list[AdvisorMessage] = Field(
        default_factory=list,
        description="Prior turns in the conversation (oldest first). Max 20 turns enforced by router.",
    )
