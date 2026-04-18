"""
Request / response schemas for POST /api/v1/advisor/chat.
"""

import uuid

from pydantic import BaseModel, Field

from app.schemas.sekem import BagrutGrade


class WizardStep(BaseModel):
    """One question-answer pair in the wizard flow."""

    question: str = Field(description="The advisor's message at this wizard step.")
    answer: str = Field(description="The choice label the user selected.")


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
    wizard_path: list[WizardStep] = Field(
        min_length=1,
        max_length=4,
        description="Ordered wizard steps taken so far (1–4 steps).",
    )
    user_profile: UserProfileCompact = Field(
        default_factory=UserProfileCompact,
        description="User's bagrut + psychometric data for personalised context.",
    )
    current_program_id: uuid.UUID | None = Field(
        default=None,
        description="ID of the program page the user is currently viewing, if any.",
    )
    target_node_id: str = Field(
        min_length=1,
        max_length=100,
        description="ID of the wizard node the user arrived at.",
    )
