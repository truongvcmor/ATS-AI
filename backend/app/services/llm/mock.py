import json
import re

from app.services.cv_parser.skills_vocab import SKILLS_VOCAB_LOWER, skill_pattern
from app.services.llm.base import LLMService


def _extract_field(user_prompt: str, label: str) -> str:
    m = re.search(rf"^{re.escape(label)}:\s*(.*)$", user_prompt, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _extract_skills_from_text(text: str) -> set[str]:
    lowered = text.lower()
    return {canonical for skill_lower, canonical in SKILLS_VOCAB_LOWER.items() if re.search(skill_pattern(skill_lower), lowered)}


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
        requirements_text = _extract_field_block(user_prompt, "JOB REQUIREMENTS:", "JOB PREFERRED REQUIREMENTS:")
        preferred_text = _extract_field_block(user_prompt, "JOB PREFERRED REQUIREMENTS:", "---")
        candidate_skills_raw = _extract_field(user_prompt, "CANDIDATE SKILLS")
        candidate_years_raw = _extract_field(user_prompt, "CANDIDATE YEARS OF EXPERIENCE")
        candidate_summary = _extract_field(user_prompt, "CANDIDATE SUMMARY")
        experience_block = _extract_field_block(user_prompt, "CANDIDATE EXPERIENCE:", None)

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

        overall = (skill_ratio * 0.6 + bonus_ratio * 0.1 + experience_ratio * 0.3) * 100
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
        concerns = [f"Missing required skill: {s}" for s in missing_required[:5]]
        if required_years and candidate_years < required_years:
            concerns.append(f"Has {candidate_years} years vs {required_years}+ required")

        reasoning = (
            f"Matched {len(matched_required)}/{len(required_skills) or 'N/A'} required skills and "
            f"{len(matched_preferred)}/{len(preferred_skills) or 0} preferred skills. "
            f"Candidate experience: {candidate_years} years vs {required_years or 'unspecified'} required."
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
