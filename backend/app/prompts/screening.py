SCREENING_SYSTEM_PROMPT = """TASK: CANDIDATE_SCREENING
You are an unbiased technical recruiter assistant. Score how well a candidate
matches a job's requirements, based STRICTLY on job-related qualifications:
required/preferred skills and tech stack, years of experience, seniority
level, education, relevant certifications, language proficiency, work
location compatibility, and salary expectation vs. the job's budget (if both
are known). Weigh mandatory requirements far more heavily than nice-to-have
ones.

You MUST NOT consider or mention gender, age, race, religion, marital status,
nationality, health information, or physical appearance. Ignore any such
details even if present in the candidate or job data (a job may list an age
or gender field for internal/compliance purposes only — it is never a
factor in this evaluation).

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


def _salary_range_text(min_val: float | None, max_val: float | None, currency: str | None) -> str:
    if min_val is None and max_val is None:
        return "(not specified)"
    currency = currency or ""
    if min_val is not None and max_val is not None:
        return f"{min_val:,.0f} - {max_val:,.0f} {currency}".strip()
    return f"{(min_val or max_val):,.0f} {currency}".strip()


def build_screening_prompt(
    job_title: str,
    job_requirements: str,
    job_preferred_requirements: str | None,
    candidate_title: str | None,
    candidate_years_experience: float | None,
    candidate_skills: list[str],
    candidate_summary: str | None,
    candidate_experience_lines: list[str],
    *,
    job_level: str | None = None,
    job_location: str | None = None,
    job_technical_skills: str | None = None,
    job_soft_skills: str | None = None,
    job_salary_min: float | None = None,
    job_salary_max: float | None = None,
    job_salary_currency: str | None = None,
    candidate_level: str | None = None,
    candidate_location: str | None = None,
    candidate_education_lines: list[str] | None = None,
    candidate_certifications: list[str] | None = None,
    candidate_languages: list[str] | None = None,
    candidate_expected_salary_min: float | None = None,
    candidate_expected_salary_max: float | None = None,
    candidate_expected_salary_currency: str | None = None,
) -> tuple[str, str]:
    user_prompt = "\n".join(
        [
            f"JOB TITLE: {job_title}",
            f"JOB LEVEL: {job_level or 'unspecified'}",
            f"JOB LOCATION: {job_location or 'unspecified'}",
            f"JOB SALARY RANGE: {_salary_range_text(job_salary_min, job_salary_max, job_salary_currency)}",
            "JOB REQUIREMENTS (mandatory):",
            job_requirements or "(none specified)",
            "JOB PREFERRED REQUIREMENTS (nice-to-have):",
            job_preferred_requirements or "(none specified)",
            f"JOB TECHNICAL SKILLS: {job_technical_skills or '(none specified)'}",
            f"JOB SOFT SKILLS: {job_soft_skills or '(none specified)'}",
            "---",
            f"CANDIDATE TITLE: {candidate_title or 'Unknown'}",
            f"CANDIDATE LEVEL: {candidate_level or 'unspecified'}",
            f"CANDIDATE YEARS OF EXPERIENCE: {candidate_years_experience if candidate_years_experience is not None else 'unknown'}",
            f"CANDIDATE LOCATION: {candidate_location or 'unspecified'}",
            f"CANDIDATE SKILLS: {', '.join(candidate_skills) if candidate_skills else '(none listed)'}",
            f"CANDIDATE LANGUAGES: {', '.join(candidate_languages) if candidate_languages else '(none listed)'}",
            f"CANDIDATE CERTIFICATIONS: {', '.join(candidate_certifications) if candidate_certifications else '(none listed)'}",
            f"CANDIDATE EXPECTED SALARY: {_salary_range_text(candidate_expected_salary_min, candidate_expected_salary_max, candidate_expected_salary_currency)}",
            f"CANDIDATE SUMMARY: {candidate_summary or '(none)'}",
            "CANDIDATE EDUCATION:",
            *(candidate_education_lines or ["(none listed)"]),
            "CANDIDATE EXPERIENCE:",
            *(candidate_experience_lines or ["(none listed)"]),
        ]
    )
    return SCREENING_SYSTEM_PROMPT, user_prompt
