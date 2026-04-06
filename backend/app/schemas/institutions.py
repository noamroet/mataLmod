from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import InstitutionType


class InstitutionResponse(BaseModel):
    """Public representation of an institution row."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name_he: str
    name_en: str
    type: InstitutionType
    location: str
    city: str
    website_url: str
    is_active: bool
    created_at: datetime
