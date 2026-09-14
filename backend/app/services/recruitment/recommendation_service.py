import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.job import Job
from app.models.screening import ScreeningResult
from app.prompts.explanation import build_explanation_prompt
from app.schemas.recommendation import CandidateRecommendation
from app.services.candidate.candidate_service import candidate_load_options
from app.services.candidate.mappers import to_list_item
from app.services.cv_parser.skills_vocab import SKILLS_VOCAB_LOWER, skill_pattern
from app.services.embedding.factory import get_embedding_service
from app.services.llm.base import LLMService
from app.services.search.hybrid import HybridSearch
from app.services.search.keyword import KeywordSearch
from app.services.search.semantic import SemanticSearch
from app.services.search.service import candidate_document_text

YEARS_RE = re.compile(r"(\d+)\+?\s*years?", re.IGNORECASE)

WEIGHTS = {"keyword": 0.15, "semantic": 0.25, "skill": 0.30, "experience": 0.15, "screening": 0.15}


def _extract_skills(text: str) -> set[str]:
    lowered = text.lower()
    return {canonical for skill_lower, canonical in SKILLS_VOCAB_LOWER.items() if re.search(skill_pattern(skill_lower), lowered)}


def _required_years(text: str) -> float:
    m = YEARS_RE.search(text)
    return float(m.group(1)) if m else 0.0


class RecommendationService:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    def find_candidates_for_job(self, db: Session, job: Job, limit: int = 20) -> list[CandidateRecommendation]:
        candidates = list(
            db.execute(
                select(Candidate).where(Candidate.merged_into_id.is_(None)).options(*candidate_load_options())
            )
            .unique()
            .scalars()
            .all()
        )
        if not candidates:
            return []

        job_text = " ".join(filter(None, [job.title, job.description, job.requirements, job.preferred_requirements]))
        required_skills = _extract_skills((job.requirements or "") + " " + (job.preferred_requirements or ""))
        required_years = _required_years(job.requirements or "")

        keyword_search = KeywordSearch()
        keyword_terms = [(t.lower(), True) for t in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]{2,}", job_text)]
        keyword_groups = [keyword_terms] if keyword_terms else []

        semantic_scores = SemanticSearch(get_embedding_service()).search(db, job_text, [c.id for c in candidates])

        screening_by_candidate = {
            row.candidate_id: row.overall_score
            for row in db.execute(
                select(ScreeningResult).where(ScreeningResult.job_id == job.id)
            ).scalars()
        }

        results: list[CandidateRecommendation] = []
        for candidate in candidates:
            doc = candidate_document_text(candidate)
            keyword_score = keyword_search.score(doc, keyword_groups) if keyword_groups else 0.0
            semantic_score = semantic_scores.get(candidate.id, 0.0)

            candidate_skills = {cs.skill.name for cs in candidate.skills}
            matched_skills = sorted(required_skills & candidate_skills)
            missing_skills = sorted(required_skills - candidate_skills)
            skill_score = (len(matched_skills) / len(required_skills)) if required_skills else 0.5

            if required_years > 0:
                experience_score = min(1.0, (candidate.years_of_experience or 0) / required_years)
            else:
                experience_score = 0.5

            raw_screening = screening_by_candidate.get(candidate.id)
            screening_score = (raw_screening / 100.0) if raw_screening is not None else None

            weights = dict(WEIGHTS)
            if screening_score is None:
                dropped = weights.pop("screening")
                total = sum(weights.values())
                weights = {k: v + (v / total) * dropped for k, v in weights.items()}

            final = (
                keyword_score * weights["keyword"]
                + semantic_score * weights["semantic"]
                + skill_score * weights["skill"]
                + experience_score * weights["experience"]
                + (screening_score or 0.0) * weights.get("screening", 0.0)
            )
            final_score = round(final * 100, 1)

            explanation = self._explain(job.title, matched_skills, missing_skills, candidate.years_of_experience, final_score)

            results.append(
                CandidateRecommendation(
                    candidate=to_list_item(candidate),
                    final_score=final_score,
                    keyword_score=round(keyword_score * 100, 1),
                    semantic_score=round(semantic_score * 100, 1),
                    skill_match_score=round(skill_score * 100, 1),
                    experience_score=round(experience_score * 100, 1),
                    screening_score=raw_screening,
                    matched_skills=matched_skills,
                    missing_skills=missing_skills,
                    explanation=explanation,
                )
            )

        results.sort(key=lambda r: r.final_score, reverse=True)
        return results[:limit]



    def _explain(
        self, job_title: str, matched: list[str], missing: list[str], years: float | None, final_score: float
    ) -> str:
        system_prompt, user_prompt = build_explanation_prompt(job_title, matched, missing, years, final_score)
        try:
            return self._llm.complete(system_prompt, user_prompt)
        except Exception:  # noqa: BLE001
            return f"Scored {final_score}/100 for {job_title}: matched {len(matched)} required skill(s), missing {len(missing)}."
