from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.search import CandidateSearchParams, SearchResponse, SearchResultItem, SortBy
from app.services.candidate.mappers import to_list_item
from app.services.search.service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/candidates", response_model=SearchResponse)
def search_candidates(
    db: DbSession,
    current_user: CurrentUser,
    q: str | None = None,
    semantic: bool = False,
    skills: list[str] = Query(default=[]),
    min_experience: float | None = None,
    locations: list[str] = Query(default=[]),
    labels: list[str] = Query(default=[]),
    min_ai_score: float | None = None,
    sort_by: SortBy = SortBy.RELEVANCE,
    page: int = 1,
    page_size: int = 20,
) -> SearchResponse:
    params = CandidateSearchParams(
        q=q,
        semantic=semantic,
        skills=skills,
        min_experience=min_experience,
        locations=locations,
        labels=labels,
        min_ai_score=min_ai_score,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    items, relevance, total = SearchService().search(db, params)
    result_items = [
        SearchResultItem(**to_list_item(c).model_dump(), relevance_score=relevance.get(c.id)) for c in items
    ]
    return SearchResponse(items=result_items, total=total, page=page, page_size=page_size)
