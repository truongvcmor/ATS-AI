import json
import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.job import Job
from app.models.screening import ScreeningResult
from app.prompts.screening import build_screening_prompt
from app.schemas.screening import ScreeningLLMOutput
from app.services.candidate.candidate_service import log_activity
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def _experience_lines(candidate: Candidate) -> list[str]:
    lines = []
    for exp in candidate.experiences:
        period = f"{exp.start_date or '?'} - {'Present' if exp.is_current else (exp.end_date or '?')}"
        lines.append(f"- {exp.position} at {exp.company} ({period}): {exp.description or ''}".strip())
    return lines


class ScreeningService:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    def _run_llm(self, job: Job, candidate: Candidate) -> ScreeningLLMOutput:
        system_prompt, user_prompt = build_screening_prompt(
            job_title=job.title,
            job_requirements=job.requirements or "",
            job_preferred_requirements=job.preferred_requirements,
            candidate_title=candidate.current_title,
            candidate_years_experience=candidate.years_of_experience,
            candidate_skills=[cs.skill.name for cs in candidate.skills],
            candidate_summary=candidate.summary,
            candidate_experience_lines=_experience_lines(candidate),
        )
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                raw = self._llm.complete(system_prompt, user_prompt)
                data = json.loads(_strip_code_fences(raw))
                return ScreeningLLMOutput.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning("Screening attempt %s/%s produced invalid output: %s", attempt, MAX_RETRIES + 1, exc)
        raise RuntimeError(f"Screening failed validation after {MAX_RETRIES + 1} attempts") from last_error

    def screen(self, db: Session, job: Job, candidate: Candidate) -> ScreeningResult:
        output = self._run_llm(job, candidate)

        result = ScreeningResult(
            candidate_id=candidate.id,
            job_id=job.id,
            overall_score=output.overall_score,
            recommendation=output.recommendation,
            matched_requirements=output.matched_requirements,
            missing_requirements=output.missing_requirements,
            strengths=output.strengths,
            concerns=output.concerns,
            reasoning=output.reasoning,
        )
        db.add(result)

        candidate.ai_score = output.overall_score
        log_activity(
            db,
            candidate_id=candidate.id,
            type_="AI_SCREENING",
            description=f"AI Screening for '{job.title}' -> {output.recommendation} (score {output.overall_score})",
            metadata={"job_id": str(job.id), "score": output.overall_score, "recommendation": output.recommendation},
        )
        db.commit()
        db.refresh(result)
        return result
