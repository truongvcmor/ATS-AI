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


def _education_lines(candidate: Candidate) -> list[str]:
    lines = []
    for edu in candidate.educations:
        period = f"{edu.start_date or '?'} - {edu.end_date or '?'}"
        lines.append(f"- {edu.degree or 'Degree'} at {edu.school} ({period})".strip())
    return lines


def _language_entries(candidate: Candidate) -> list[str]:
    return [f"{lang.name} ({lang.proficiency})" if lang.proficiency else lang.name for lang in candidate.languages]


def _certification_names(candidate: Candidate) -> list[str]:
    return [cert.name for cert in candidate.certifications]


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
            job_level=job.level.value if job.level else None,
            job_location=job.location,
            job_technical_skills=job.technical_skills,
            job_soft_skills=job.soft_skills,
            job_salary_min=float(job.salary_min) if job.salary_min is not None else None,
            job_salary_max=float(job.salary_max) if job.salary_max is not None else None,
            job_salary_currency=job.salary_currency.value if job.salary_currency else None,
            candidate_level=candidate.current_level.value if candidate.current_level else None,
            candidate_location=candidate.location,
            candidate_education_lines=_education_lines(candidate),
            candidate_certifications=_certification_names(candidate),
            candidate_languages=_language_entries(candidate),
            candidate_expected_salary_min=float(candidate.expected_salary_min) if candidate.expected_salary_min is not None else None,
            candidate_expected_salary_max=float(candidate.expected_salary_max) if candidate.expected_salary_max is not None else None,
            candidate_expected_salary_currency=candidate.expected_salary_currency.value if candidate.expected_salary_currency else None,
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
