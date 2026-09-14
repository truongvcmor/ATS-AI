import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ProcessingStatus


class ProcessingJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    file_name: str
    candidate_id: uuid.UUID | None = None
    status: ProcessingStatus
    error_message: str | None = None
    duplicate_of_candidate_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    jobs: list[ProcessingJobOut]
