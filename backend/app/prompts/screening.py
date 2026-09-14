SCREENING_SYSTEM_PROMPT = """TASK: CANDIDATE_SCREENING
You are an unbiased technical recruiter assistant. Score how well a candidate
matches a job's requirements, based STRICTLY on job-related qualifications and
experience (skills, years of experience, domain background, achievements).

You MUST NOT consider or mention gender, age, race, religion, marital status,
nationality, health information, or physical appearance. Ignore any such
details even if present in the candidate data.

Return ONLY valid JSON matching exactly this schema (no markdown fences):
{
  "overall_score": integer 0-100,
  "recommendation": "STRONG_MATCH" | "MATCH" | "POSSIBLE_MATCH" | "WEAK_MATCH",
  "matched_requirements": string[],
  "missing_requirements": string[],
  "strengths": string[],
  "concerns": string[],
  "reasoning": string
}
Score bands: STRONG_MATCH >= 85, MATCH >= 70, POSSIBLE_MATCH >= 50, otherwise WEAK_MATCH.
"""


def build_screening_prompt(
    job_title: str,
    job_requirements: str,
    job_preferred_requirements: str | None,
    candidate_title: str | None,
    candidate_years_experience: float | None,
    candidate_skills: list[str],
    candidate_summary: str | None,
    candidate_experience_lines: list[str],
) -> tuple[str, str]:
    user_prompt = "\n".join(
        [
            f"JOB TITLE: {job_title}",
            "JOB REQUIREMENTS:",
            job_requirements or "(none specified)",
            "JOB PREFERRED REQUIREMENTS:",
            job_preferred_requirements or "(none specified)",
            "---",
            f"CANDIDATE TITLE: {candidate_title or 'Unknown'}",
            f"CANDIDATE YEARS OF EXPERIENCE: {candidate_years_experience if candidate_years_experience is not None else 'unknown'}",
            f"CANDIDATE SKILLS: {', '.join(candidate_skills) if candidate_skills else '(none listed)'}",
            f"CANDIDATE SUMMARY: {candidate_summary or '(none)'}",
            "CANDIDATE EXPERIENCE:",
            *(candidate_experience_lines or ["(none listed)"]),
        ]
    )
    return SCREENING_SYSTEM_PROMPT, user_prompt
