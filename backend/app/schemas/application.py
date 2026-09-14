import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PipelineStageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    order: int
    is_terminal: bool


class ApplicationCreate(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID


class ApplicationStageUpdate(BaseModel):
    stage_id: uuid.UUID


class ApplicationCandidateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    current_title: str | None = None
    ai_score: float | None = None
    location: str | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    current_stage_id: uuid.UUID
    applied_at: datetime
    updated_at: datetime
    candidate: ApplicationCandidateSummary | None = None
