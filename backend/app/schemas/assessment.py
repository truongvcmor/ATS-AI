import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AssessmentRecommendation


class AssessmentCreate(BaseModel):
    job_id: uuid.UUID | None = None
    interview_type: str
    interviewer: str
    score: float | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    comments: str | None = None
    recommendation: AssessmentRecommendation


class AssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID | None = None
    interview_type: str
    interviewer: str
    score: float | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    comments: str | None = None
    recommendation: AssessmentRecommendation
    created_at: datetime
