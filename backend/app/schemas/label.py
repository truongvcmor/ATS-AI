import uuid

from pydantic import BaseModel, ConfigDict


class LabelCreate(BaseModel):
    name: str
    color: str = "#6366f1"


class LabelUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class LabelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    color: str
    candidate_count: int = 0
