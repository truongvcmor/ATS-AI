# API Reference

Interactive OpenAPI docs (always the source of truth): `http://localhost:8080/docs` (Swagger UI) or `http://localhost:8080/redoc`.

Base URL: `http://localhost:8080/api` (Docker Compose) — everything below is relative to that.

All endpoints except `POST /auth/register` and `POST /auth/login` require `Authorization: Bearer <token>`. Errors are returned as `{"detail": "..."}` with a 4xx/5xx status.

## Auth

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/auth/register` | `{email, password, full_name, role}` | `role` one of `ADMIN`, `RECRUITER`, `HIRING_MANAGER` |
| POST | `/auth/login` | form-encoded `username`, `password` | returns `{access_token, token_type, user}` |
| GET | `/auth/me` | — | current user |

## Candidates / Talent Pool

| Method | Path | Notes |
|---|---|---|
| POST | `/candidates/upload` | multipart, repeated `files` field; accepts `.pdf`, `.docx`, `.png`, `.jpg`/`.jpeg` (images and no-text-layer scanned PDFs are OCR'd automatically); returns `202 {jobs: [ProcessingJobOut]}` immediately, processing runs in the background |
| GET | `/candidates/processing` | recent processing jobs |
| GET | `/candidates/processing/{job_id}` | poll for status: `UPLOADING → PARSING → PROCESSING → INDEXING → COMPLETED/FAILED` |
| POST | `/candidates/processing/{job_id}/retry` | re-run a failed job (RecruiterOrAdmin) |
| GET | `/candidates` | paginated Talent Pool list; query params below |
| GET | `/candidates/{id}` | full candidate profile |
| PATCH | `/candidates/{id}` | update editable fields (RecruiterOrAdmin) |
| DELETE | `/candidates/{id}` | hard delete, cascades all related records (RecruiterOrAdmin) |
| POST | `/candidates/{id}/merge` | `{source_candidate_id, target_candidate_id}`, target must equal `{id}` (RecruiterOrAdmin) |
| GET | `/candidates/{id}/history` | activity timeline, newest first |
| GET/POST | `/candidates/{id}/assessments` | list / create an interview assessment |
| GET | `/candidates/{id}/screening` | AI screening history for this candidate |
| POST/DELETE | `/candidates/{id}/labels/{label_id}` | attach/remove a label (RecruiterOrAdmin) |
| GET | `/candidates/{id}/cvs/{cv_id}/download` | download the original file |

List/search query params (both `GET /candidates` and `GET /search/candidates` accept the same set):

- `q` — keyword query, supports `AND`/`OR`/`-exclude`/quoted phrases (e.g. `Python AND FastAPI`, `Python OR Java`, `Python -PHP`)
- `semantic=true` — treat `q` as a natural-language semantic query instead of the boolean DSL
- `skills`, `locations`, `labels` — repeatable (`?skills=Python&skills=FastAPI`)
- `min_experience`, `min_ai_score` — numeric filters
- `sort_by` — `relevance | ai_score | experience | recently_added | recently_updated`
- `page`, `page_size`

## Jobs

| Method | Path | Notes |
|---|---|---|
| POST | `/jobs` | create (RecruiterOrAdmin); default pipeline stages are created automatically |
| GET | `/jobs` | list, optional `?status_filter=` |
| GET | `/jobs/{id}` | detail (includes `application_count`) |
| PATCH | `/jobs/{id}` | update (RecruiterOrAdmin) |
| DELETE | `/jobs/{id}` | delete + cascades applications/stages/screenings (RecruiterOrAdmin) |
| GET | `/jobs/{id}/stages` | this job's pipeline stages, ordered |
| GET | `/jobs/{id}/candidates` | applications for this job (Kanban board data) |
| POST | `/jobs/{id}/screen` | `{job_id, candidate_ids?}` — AI-screen specific candidates, or all current applicants if omitted (RecruiterOrAdmin) |
| POST | `/jobs/{id}/recommendations` | "Find candidates for this job" — ranked list with per-candidate explanation |

Job fields also include `level`, `salary_min`/`salary_max`/`salary_currency`/`salary_negotiable`, `working_hours`, `benefits`, `hiring_reason`, `technical_skills`, `soft_skills`, and `age_min`/`age_max`/`gender_requirement`. The last three are **informational only** — recorded for internal/compliance purposes but never read by AI screening or recommendation scoring.

Candidate profile fields also include `portfolio_url`, `current_level`, `primary_specialty` (all inferred from the CV where possible), and `expected_salary_min`/`expected_salary_max`/`expected_salary_currency` (usually set manually via `PATCH /candidates/{id}`, since CVs rarely state salary expectations).

AI screening (`/jobs/{id}/screen`) and recommendations (`/jobs/{id}/recommendations`) both weigh: required/preferred skills, years of experience, seniority level, education, relevant certifications, language proficiency, location compatibility, and expected-salary-vs-budget fit. A dimension is only scored when both sides have data for it (e.g. an unscored expected salary doesn't penalize a candidate); weights are redistributed proportionally across whichever dimensions are present.

## Applications / Pipeline

| Method | Path | Notes |
|---|---|---|
| POST | `/applications` | `{candidate_id, job_id}` (RecruiterOrAdmin) |
| PATCH | `/applications/{id}/stage` | `{stage_id}` — move a candidate between Kanban columns (RecruiterOrAdmin) |

## Labels

| Method | Path | Notes |
|---|---|---|
| POST | `/labels` | `{name, color}` (RecruiterOrAdmin) |
| GET | `/labels` | list with `candidate_count` |
| PATCH | `/labels/{id}` | rename/recolor (RecruiterOrAdmin) |
| DELETE | `/labels/{id}` | (RecruiterOrAdmin) |

## Dashboard

| Method | Path | Notes |
|---|---|---|
| GET | `/dashboard` | KPIs + candidates-over-time, by-source, top-skills, top-locations, pipeline-by-stage, AI-score-distribution |

## Settings (Admin only)

| Method | Path | Notes |
|---|---|---|
| GET | `/settings/ai` | Effective AI provider config — resolved values, masked key previews (`****abcd`), and whether each came from the database or `.env` |
| PUT | `/settings/ai` | Partial update — omit a field to leave it untouched; send `openai_api_keys`/`gemini_api_keys` as `""` to clear the override and revert to `.env`. Applies immediately, no restart. |
| POST | `/settings/ai/test` | `{provider, api_key?, model?}` — makes one real minimal completion call to verify a key works before saving it; returns `{ok, message, latency_ms}` |

## Response shape examples

```jsonc
// GET /candidates/{id}
{
  "id": "...", "full_name": "Nguyen Van A", "current_title": "Senior Backend Engineer",
  "years_of_experience": 6.0, "location": "Ho Chi Minh City", "email": "...", "ai_score": 88.8,
  "status": "NEW", "skills": ["Python", "FastAPI", "RAG", "..."],
  "labels": [{"id": "...", "name": "AI Engineer", "color": "#22c55e"}],
  "phone": "...", "summary": "...", "source": "upload",
  "experiences": [{"company": "...", "position": "...", "start_date": "2021-01-01", "end_date": null, "is_current": true, "description": "..."}],
  "educations": [...], "certifications": [...], "languages": [...], "projects": [...],
  "cvs": [{"id": "...", "file_name": "cv.docx", "extraction_method": "text", "is_primary": true, "uploaded_at": "..."}]
}

// POST /jobs/{id}/recommendations
{
  "job_id": "...",
  "recommendations": [
    {
      "candidate": { "...CandidateListItem..." },
      "final_score": 88.8, "keyword_score": 92.0, "semantic_score": 36.6,
      "skill_match_score": 100.0, "experience_score": 100.0, "screening_score": 100.0,
      "matched_skills": ["FastAPI", "LLM", "LangChain", "Python", "Qdrant", "RAG"],
      "missing_skills": [],
      "explanation": "This candidate scores 88.8/100 for the Senior Python AI Engineer role. Strong alignment on FastAPI, LLM, LangChain, Python, Qdrant, RAG."
    }
  ]
}
```

**AI-generated recommendation disclaimer**: every screening result and recommendation is explicitly an AI-generated suggestion — the frontend surfaces this and always leaves the final decision to the recruiter.
