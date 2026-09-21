import uuid

from pydantic import BaseModel

from app.schemas.candidate import CandidateListItem


class CandidateRecommendation(BaseModel):
    candidate: CandidateListItem
    final_score: float
    keyword_score: float
    semantic_score: float
    skill_match_score: float
    experience_score: float
    level_score: float | None
    location_score: float | None
    screening_score: float | None
    matched_skills: list[str]
    missing_skills: list[str]
    explanation: str


class RecommendationResponse(BaseModel):
    job_id: uuid.UUID
    recommendations: list[CandidateRecommendation]
