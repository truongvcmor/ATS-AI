from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate, CandidateSkill, Skill
from app.models.label import CandidateLabel, Label
from app.schemas.search import CandidateSearchParams, SortBy
from app.services.candidate.candidate_service import candidate_load_options
from app.services.embedding.factory import get_embedding_service
from app.services.search.hybrid import HybridSearch
from app.services.search.keyword import KeywordSearch, parse_query
from app.services.search.semantic import SemanticSearch


def candidate_document_text(candidate: Candidate) -> str:
    parts = [candidate.full_name, candidate.current_title or "", candidate.summary or "", candidate.location or ""]
    parts += [cs.skill.name for cs in candidate.skills]
    for exp in candidate.experiences:
        parts.append(f"{exp.position} {exp.company} {exp.description or ''}")
    for edu in candidate.educations:
        parts.append(f"{edu.school} {edu.degree or ''} {edu.major or ''}")
    return " \n".join(p for p in parts if p)


class SearchService:
    def __init__(self) -> None:
        self._keyword = KeywordSearch()
        self._hybrid = HybridSearch()

    def _base_query(self, params: CandidateSearchParams):
        stmt = select(Candidate).where(Candidate.merged_into_id.is_(None)).options(*candidate_load_options())

        if params.skills:
            for skill_name in params.skills:
                stmt = stmt.where(
                    Candidate.id.in_(
                        select(CandidateSkill.candidate_id)
                        .join(Skill, Skill.id == CandidateSkill.skill_id)
                        .where(Skill.name.ilike(skill_name))
                    )
                )
        if params.min_experience is not None:
            stmt = stmt.where(Candidate.years_of_experience >= params.min_experience)
        if params.locations:
            stmt = stmt.where(or_(*[Candidate.location.ilike(f"%{loc}%") for loc in params.locations]))
        if params.labels:
            for label_name in params.labels:
                stmt = stmt.where(
                    Candidate.id.in_(
                        select(CandidateLabel.candidate_id)
                        .join(Label, Label.id == CandidateLabel.label_id)
                        .where(Label.name.ilike(label_name))
                    )
                )
        if params.min_ai_score is not None:
            stmt = stmt.where(Candidate.ai_score >= params.min_ai_score)
        return stmt

    def search(self, db: Session, params: CandidateSearchParams) -> tuple[list[Candidate], dict, int]:
        stmt = self._base_query(params)
        candidates = list(db.execute(stmt).unique().scalars().all())

        keyword_scores: dict = {}
        semantic_scores: dict = {}

        if params.q and params.q.strip():
            if params.semantic:
                semantic_search = SemanticSearch(get_embedding_service())
                semantic_scores = semantic_search.search(db, params.q, [c.id for c in candidates])
            else:
                groups = parse_query(params.q)
                filtered = []
                for c in candidates:
                    doc = candidate_document_text(c)
                    if self._keyword.matches(doc, groups):
                        keyword_scores[c.id] = self._keyword.score(doc, groups)
                        filtered.append(c)
                candidates = filtered

        relevance = self._hybrid.combine(keyword_scores, semantic_scores)

        candidates = self._sort(candidates, params.sort_by, relevance)
        total = len(candidates)
        start = (params.page - 1) * params.page_size
        page_items = candidates[start : start + params.page_size]
        return page_items, relevance, total

    def _sort(self, candidates: list[Candidate], sort_by: SortBy, relevance: dict) -> list[Candidate]:
        if sort_by == SortBy.AI_SCORE:
            return sorted(candidates, key=lambda c: c.ai_score or 0, reverse=True)
        if sort_by == SortBy.EXPERIENCE:
            return sorted(candidates, key=lambda c: c.years_of_experience or 0, reverse=True)
        if sort_by == SortBy.RECENTLY_ADDED:
            return sorted(candidates, key=lambda c: c.created_at, reverse=True)
        if sort_by == SortBy.RECENTLY_UPDATED:
            return sorted(candidates, key=lambda c: c.updated_at, reverse=True)
        # RELEVANCE: only meaningful with a query; otherwise fall back to recently updated.
        if relevance:
            return sorted(candidates, key=lambda c: relevance.get(c.id, 0), reverse=True)
        return sorted(candidates, key=lambda c: c.updated_at, reverse=True)
