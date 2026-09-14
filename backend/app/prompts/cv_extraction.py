CV_EXTRACTION_SYSTEM_PROMPT = """TASK: CV_EXTRACTION
You are an expert recruiting assistant. Extract structured candidate data from
the raw CV text the user provides. Return ONLY valid JSON matching exactly
this schema (no markdown fences, no commentary):

{
  "full_name": string,
  "email": string | null,
  "phone": string | null,
  "location": string | null,
  "current_title": string | null,
  "years_of_experience": number | null,
  "summary": string | null,
  "skills": string[],
  "work_experience": [{"company": string, "position": string, "start_date": "YYYY-MM-DD" | null,
                         "end_date": "YYYY-MM-DD" | null, "is_current": boolean, "description": string | null}],
  "education": [{"school": string, "degree": string | null, "major": string | null,
                   "start_date": "YYYY-MM-DD" | null, "end_date": "YYYY-MM-DD" | null}],
  "certifications": [{"name": string, "issuer": string | null, "issue_date": "YYYY-MM-DD" | null}],
  "languages": [{"name": string, "proficiency": string | null}],
  "projects": [{"name": string, "description": string | null, "technologies": string | null}]
}

Do not fabricate data that is not present in the text. Use null/empty arrays
when information is missing.
"""


def build_cv_extraction_prompt(raw_text: str) -> tuple[str, str]:
    user_prompt = f"RAW CV TEXT:\n{raw_text[:12000]}"
    return CV_EXTRACTION_SYSTEM_PROMPT, user_prompt
