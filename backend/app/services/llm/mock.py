import json
import re

from app.services.cv_parser.skills_vocab import SKILLS_VOCAB_LOWER, skill_pattern
from app.services.llm.base import LLMService

LEVEL_ORDER = ["INTERN", "FRESHER", "JUNIOR", "MID", "SENIOR", "LEAD", "MANAGER", "DIRECTOR"]

LANGUAGE_KEYWORDS = ["english", "japanese", "vietnamese", "chinese", "korean", "french", "german", "spanish"]


def _extract_field(user_prompt: str, label: str) -> str:
    m = re.search(rf"^{re.escape(label)}:\s*(.*)$", user_prompt, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _extract_skills_from_text(text: str) -> set[str]:
    lowered = text.lower()
    return {canonical for skill_lower, canonical in SKILLS_VOCAB_LOWER.items() if re.search(skill_pattern(skill_lower), lowered)}


def _level_score(job_level: str, candidate_level: str) -> float | None:
    if not job_level or job_level == "unspecified" or not candidate_level or candidate_level == "unspecified":
        return None
    try:
        job_idx = LEVEL_ORDER.index(job_level.upper())
        candidate_idx = LEVEL_ORDER.index(candidate_level.upper())
    except ValueError:
        return None
    diff = candidate_idx - job_idx
    if diff >= 0:
        return 1.0
    return max(0.0, 1.0 + diff * 0.25)


def _required_languages(text: str) -> set[str]:
    lowered = text.lower()
    return {lang for lang in LANGUAGE_KEYWORDS if re.search(rf"\b{lang}\b", lowered)}


def _candidate_languages(raw: str) -> set[str]:
    lowered = raw.lower()
    return {lang for lang in LANGUAGE_KEYWORDS if lang in lowered}


def _mentions_certification_requirement(text: str) -> bool:
    return bool(re.search(r"certificat", text, re.IGNORECASE))


def _location_score(job_location: str, candidate_location: str) -> float | None:
    if not job_location or job_location == "unspecified" or not candidate_location or candidate_location == "unspecified":
        return None
    job_loc = job_location.strip().lower()
    candidate_loc = candidate_location.strip().lower()
    if job_loc in candidate_loc or candidate_loc in job_loc:
        return 1.0
    if "remote" in job_loc:
        return 1.0
    return 0.3


def _parse_salary_range(text: str) -> tuple[float | None, float | None]:
    m = re.search(r"([\d,]+)\s*-\s*([\d,]+)", text)
    if m:
        return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
    m = re.search(r"([\d,]+)", text)
    if m:
        val = float(m.group(1).replace(",", ""))
        return val, val
    return None, None


class MockLLMService(LLMService):
    """Deterministic, rule-based stand-in for a real LLM.

    Dispatches on the `TASK:` marker every prompt in app/prompts/ starts
    with, so the exact same call sites (screening service, explanation
    builder) work unmodified whether LLM_PROVIDER is "mock" or "openai".
    Never calls out to the network — the product works with zero API keys.
    """

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        task_match = re.search(r"TASK:\s*(\w+)", system_prompt)
        task = task_match.group(1) if task_match else ""
        if task == "CANDIDATE_SCREENING":
            return self._screen(user_prompt)
        if task == "CANDIDATE_EXPLANATION":
            return self._explain(user_prompt)
        raise ValueError(f"MockLLMService cannot handle unknown task: {task}")

    def _screen(self, user_prompt: str) -> str:
        requirements_text = _extract_field_block(user_prompt, "JOB REQUIREMENTS", "JOB PREFERRED REQUIREMENTS")
        preferred_text = _extract_field_block(user_prompt, "JOB PREFERRED REQUIREMENTS", "JOB TECHNICAL SKILLS")
        candidate_skills_raw = _extract_field(user_prompt, "CANDIDATE SKILLS")
        candidate_years_raw = _extract_field(user_prompt, "CANDIDATE YEARS OF EXPERIENCE")
        candidate_summary = _extract_field(user_prompt, "CANDIDATE SUMMARY")
        experience_block = _extract_field_block(user_prompt, "CANDIDATE EXPERIENCE:", None)
        job_level = _extract_field(user_prompt, "JOB LEVEL")
        job_location = _extract_field(user_prompt, "JOB LOCATION")
        job_salary_raw = _extract_field(user_prompt, "JOB SALARY RANGE")
        candidate_level = _extract_field(user_prompt, "CANDIDATE LEVEL")
        candidate_location = _extract_field(user_prompt, "CANDIDATE LOCATION")
        candidate_languages_raw = _extract_field(user_prompt, "CANDIDATE LANGUAGES")
        candidate_certifications_raw = _extract_field(user_prompt, "CANDIDATE CERTIFICATIONS")
        candidate_salary_raw = _extract_field(user_prompt, "CANDIDATE EXPECTED SALARY")

        required_skills = sorted(_extract_skills_from_text(requirements_text))
        preferred_skills = sorted(_extract_skills_from_text(preferred_text) - set(required_skills))
        candidate_skills = {s.strip() for s in candidate_skills_raw.split(",") if s.strip()}
        candidate_full_text_skills = _extract_skills_from_text(
            candidate_skills_raw + " " + candidate_summary + " " + experience_block
        )
        candidate_skills |= candidate_full_text_skills

        matched_required = [s for s in required_skills if s in candidate_skills]
        missing_required = [s for s in required_skills if s not in candidate_skills]
        matched_preferred = [s for s in preferred_skills if s in candidate_skills]

        skill_ratio = (len(matched_required) / len(required_skills)) if required_skills else 0.7
        bonus_ratio = (len(matched_preferred) / len(preferred_skills)) if preferred_skills else 0.0

        years_required_match = re.search(r"(\d+)\+?\s*years?", requirements_text, re.IGNORECASE)
        required_years = float(years_required_match.group(1)) if years_required_match else 0.0
        try:
            candidate_years = float(candidate_years_raw)
        except ValueError:
            candidate_years = 0.0
        if required_years <= 0:
            experience_ratio = 0.7
        else:
            experience_ratio = min(1.0, candidate_years / required_years)

        level_ratio = _level_score(job_level, candidate_level)
        location_ratio = _location_score(job_location, candidate_location)

        required_languages = _required_languages(requirements_text + " " + preferred_text)
        candidate_languages = _candidate_languages(candidate_languages_raw)
        matched_languages = sorted(required_languages & candidate_languages)
        missing_languages = sorted(required_languages - candidate_languages)
        language_ratio = (len(matched_languages) / len(required_languages)) if required_languages else None

        cert_required = _mentions_certification_requirement(requirements_text)
        has_certification = bool(candidate_certifications_raw)
        cert_ratio = (1.0 if has_certification else 0.3) if cert_required else None

        weighted = [(skill_ratio, 0.40), (bonus_ratio, 0.05), (experience_ratio, 0.15)]
        for ratio, weight in (
            (level_ratio, 0.15),
            (location_ratio, 0.10),
            (language_ratio, 0.10),
            (cert_ratio, 0.05),
        ):
            if ratio is not None:
                weighted.append((ratio, weight))
        total_weight = sum(w for _, w in weighted)
        overall = sum(r * w for r, w in weighted) / total_weight * 100
        overall = round(max(0.0, min(100.0, overall)))

        if overall >= 85:
            recommendation = "STRONG_MATCH"
        elif overall >= 70:
            recommendation = "MATCH"
        elif overall >= 50:
            recommendation = "POSSIBLE_MATCH"
        else:
            recommendation = "WEAK_MATCH"

        strengths = [f"Has required skill: {s}" for s in matched_required[:5]]
        if candidate_years >= required_years and required_years > 0:
            strengths.append(f"Meets experience requirement ({candidate_years} years)")
        if level_ratio == 1.0:
            strengths.append(f"Current level ({candidate_level}) meets or exceeds target level ({job_level})")
        if matched_languages:
            strengths.append(f"Meets required language(s): {', '.join(matched_languages)}")
        if location_ratio == 1.0:
            strengths.append("Candidate location matches the job location")

        concerns = [f"Missing required skill: {s}" for s in missing_required[:5]]
        if required_years and candidate_years < required_years:
            concerns.append(f"Has {candidate_years} years vs {required_years}+ required")
        if level_ratio is not None and level_ratio < 1.0:
            concerns.append(f"Current level ({candidate_level}) is below target level ({job_level})")
        if missing_languages:
            concerns.append(f"Missing required language(s): {', '.join(missing_languages)}")
        if location_ratio is not None and location_ratio < 1.0:
            concerns.append(f"Candidate location ({candidate_location}) differs from job location ({job_location})")
        if cert_ratio is not None and cert_ratio < 1.0:
            concerns.append("Job calls for a relevant certification; none listed on candidate profile")

        job_salary_min, job_salary_max = _parse_salary_range(job_salary_raw)
        candidate_salary_min, candidate_salary_max = _parse_salary_range(candidate_salary_raw)
        if job_salary_max is not None and candidate_salary_min is not None:
            if candidate_salary_min <= job_salary_max:
                strengths.append("Expected salary fits within the job's budget")
            else:
                concerns.append(
                    f"Expected salary ({candidate_salary_raw}) exceeds the job's budget ({job_salary_raw})"
                )

        reasoning = (
            f"Matched {len(matched_required)}/{len(required_skills) or 'N/A'} required skills and "
            f"{len(matched_preferred)}/{len(preferred_skills) or 0} preferred skills. "
            f"Candidate experience: {candidate_years} years vs {required_years or 'unspecified'} required. "
            f"Level: {candidate_level or 'unspecified'} vs target {job_level or 'unspecified'}. "
            f"Location: {candidate_location or 'unspecified'} vs job location {job_location or 'unspecified'}."
        )

        result = {
            "overall_score": overall,
            "recommendation": recommendation,
            "matched_requirements": matched_required + matched_preferred,
            "missing_requirements": missing_required,
            "strengths": strengths or ["Profile reviewed against job requirements."],
            "concerns": concerns,
            "reasoning": reasoning,
        }
        return json.dumps(result)

    def _explain(self, user_prompt: str) -> str:
        job_title = _extract_field(user_prompt, "JOB TITLE")
        matched = _extract_field(user_prompt, "MATCHED SKILLS")
        missing = _extract_field(user_prompt, "MISSING SKILLS")
        score = _extract_field(user_prompt, "FINAL MATCH SCORE")
        sentence = f"This candidate scores {score}/100 for the {job_title} role."
        if matched and matched != "(none)":
            sentence += f" Strong alignment on {matched}."
        if missing and missing != "(none)":
            sentence += f" Gaps to note: {missing}."
        return sentence


def _extract_field_block(text: str, start_label: str, end_label: str | None) -> str:
    start_idx = text.find(start_label)
    if start_idx == -1:
        return ""
    start_idx += len(start_label)
    if end_label:
        end_idx = text.find(end_label, start_idx)
        if end_idx == -1:
            end_idx = len(text)
    else:
        end_idx = len(text)
    return text[start_idx:end_idx].strip()
