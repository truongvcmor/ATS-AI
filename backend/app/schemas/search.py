import uuid
from enum import Enum

from pydantic import BaseModel

from app.schemas.candidate import CandidateListItem


class SortBy(str, Enum):
    RELEVANCE = "relevance"
    AI_SCORE = "ai_score"
    EXPERIENCE = "experience"
    RECENTLY_ADDED = "recently_added"
    RECENTLY_UPDATED = "recently_updated"


class CandidateSearchParams(BaseModel):
    q: str | None = None
    semantic: bool = False
    skills: list[str] = []
    min_experience: float | None = None
    locations: list[str] = []
    labels: list[str] = []
    min_ai_score: float | None = None
    sort_by: SortBy = SortBy.RELEVANCE
    page: int = 1
    page_size: int = 20


class SearchResultItem(CandidateListItem):
    relevance_score: float | None = None


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    total: int
    page: int
    page_size: int
