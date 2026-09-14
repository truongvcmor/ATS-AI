EXPLANATION_SYSTEM_PROMPT = """TASK: CANDIDATE_EXPLANATION
You are a recruiting assistant. In 2-3 sentences, explain why a candidate is
(or isn't) a good fit for a job, based only on job-related skills and
experience. Do not mention gender, age, race, religion, or appearance.
Return plain text only, no JSON, no markdown.
"""


def build_explanation_prompt(
    job_title: str,
    matched_skills: list[str],
    missing_skills: list[str],
    years_experience: float | None,
    final_score: float,
) -> tuple[str, str]:
    user_prompt = "\n".join(
        [
            f"JOB TITLE: {job_title}",
            f"FINAL MATCH SCORE: {final_score}",
            f"MATCHED SKILLS: {', '.join(matched_skills) or '(none)'}",
            f"MISSING SKILLS: {', '.join(missing_skills) or '(none)'}",
            f"YEARS OF EXPERIENCE: {years_experience if years_experience is not None else 'unknown'}",
        ]
    )
    return EXPLANATION_SYSTEM_PROMPT, user_prompt
