import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Recommendation


class ScreeningRequest(BaseModel):
    job_id: uuid.UUID
    candidate_id: uuid.UUID


class BulkScreeningRequest(BaseModel):
    job_id: uuid.UUID
    candidate_ids: list[uuid.UUID] | None = None  # None = screen all applicants of the job


class ScreeningLLMOutput(BaseModel):
    """Shape the LLM (or mock) must produce. Validated with Pydantic; retried on failure."""

    overall_score: int = Field(ge=0, le=100)
    recommendation: Recommendation
    matched_requirements: list[str] = []
    missing_requirements: list[str] = []
    strengths: list[str] = []
    concerns: list[str] = []
    reasoning: str = ""


class ScreeningResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    overall_score: float
    recommendation: Recommendation
    matched_requirements: list[str] = []
    missing_requirements: list[str] = []
    strengths: list[str] = []
    concerns: list[str] = []
    reasoning: str | None = None
    created_at: datetime
