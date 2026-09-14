import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    description: str
    activity_metadata: dict | None = None
    created_at: datetime
    created_by: str | None = None
