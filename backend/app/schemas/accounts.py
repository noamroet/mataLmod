"""
Request / response schemas for /api/v1/accounts/* endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RoadmapProgressItem(BaseModel):
    """One checked/unchecked roadmap to-do item to persist."""

    program_id:  uuid.UUID
    item_index:  int   = Field(ge=0, description="0-based index of the to-do item")
    checked:     bool
    checked_at:  datetime = Field(
        description="Client-side timestamp when the user checked/unchecked the item."
    )


class RoadmapProgressBatch(BaseModel):
    """Batch sync of roadmap progress items from localStorage."""

    items: list[RoadmapProgressItem] = Field(
        min_length=1,
        max_length=200,
        description="All roadmap items from localStorage for this session.",
    )


class RoadmapProgressResponse(BaseModel):
    synced: int = Field(description="Number of items successfully persisted.")
