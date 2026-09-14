# Architecture

## High-level diagram

```
                    ┌───────────────┐
                    │   Frontend    │  React + TS + Vite, TanStack Query
                    └───────┬───────┘
                            │ REST (JWT bearer)
                    ┌───────▼───────┐
                    │    FastAPI    │  app/api/v1/*.py — routers only, no business logic
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┬───────────────────┐
          ▼                 ▼                 ▼                   ▼
   Candidate Service   Recruitment       Search Service      Dashboard Service
   (CRUD, merge,       Service           (keyword +          (KPI/analytics
    dup detection)     (pipeline,        semantic +          aggregation)
                        recommendations)  hybrid)
          │                 │                 │                   │
          └─────────────────┴────────┬────────┴───────────────────┘
                                      │
                              Repositories / SQLAlchemy ORM
                                      │
                              ┌───────▼───────┐
                              │  PostgreSQL   │
                              │   + pgvector  │
                              └───────┬───────┘
                                      │
                              ┌───────▼───────┐
                              │   AI Layer    │  app/services/{cv_parser,llm,embedding,screening}/
                              ├───────────────┤
                              │ CVParser      │  RuleBasedCVParser (default) | LLMCVParser
                              │ LLMService    │  MockLLMService (default)    | OpenAILLMService
                              │ Embedding     │  MockEmbeddingService (def.) | OpenAIEmbeddingService
                              │ Screening     │  validates LLM JSON w/ retry via Pydantic
                              └───────────────┘
```

AI is a *service inside* the ATS, not the whole system: every feature (CRUD, search-by-filter, pipeline, assessments) works with zero AI configured. AI only adds parsing quality, screening scores, and semantic ranking on top.

## Layering

Strict `Router → Service → Repository/ORM → DB`. Routers (`app/api/v1/*.py`) only: parse/validate the request, call one service function, map the result to a response schema. All business rules (duplicate detection, merge semantics, pipeline stage transitions, scoring) live in `app/services/*`.

```
backend/app/
  main.py                 FastAPI app, CORS, security headers, startup hook, global exception handlers
  core/                    config (pydantic-settings), runtime_config (hot-swappable AI config), crypto (secrets
                            encryption), security (JWT/bcrypt), rate_limit, deps (auth/RBAC), logging, database
  models/                  SQLAlchemy ORM, one module per aggregate (incl. system_settings.py)
  schemas/                 Pydantic request/response models
  api/v1/                  routers: auth, candidates, jobs, applications, labels, search, dashboard, settings
  services/
    ai_common/              key_pool.py: provider-agnostic KeyPool (round-robin + cooldown-on-failure),
                            shared by the LLM and embedding rotating services
    cv_parser/              CVParser ABC → RuleBasedCVParser, LLMCVParser; extractors.py (pdf/docx/image text + OCR fallback)
    llm/                    LLMService ABC → MockLLMService, OpenAILLMService, GeminiLLMService, RotatingLLMService; factory.py
    embedding/              EmbeddingService ABC → MockEmbeddingService, OpenAIEmbeddingService, GeminiEmbeddingService,
                            RotatingEmbeddingService; factory.py
    ocr/                    OCRService ABC → TesseractOCRService, LLMVisionOCRService, HybridOCRService; factory.py
    settings/                settings_service.py: admin-editable AI config (DB row ↔ core/runtime_config), key testing
    screening/              screening_service.py: prompt → LLMService → Pydantic-validated JSON, retried on failure
    search/                 KeywordSearch (boolean DSL), SemanticSearch (pgvector cosine), HybridSearch (weighted combine), service.py facade
    candidate/              candidate_service (CRUD/activity log), duplicate_detection, merge_service, mappers (ORM → API schema)
    recruitment/            pipeline_service (stages/applications), recommendation_service ("find candidates for job")
    dashboard/              KPI + analytics aggregation
  workers/cv_processing.py  the async upload → parse → normalize → dedupe → embed → index pipeline
  prompts/                  all LLM prompt templates (never inline in routes/services)
  utils/                    file storage (incl. magic-byte content validation), text normalization
  seed.py / seed_data.py    demo data generator
alembic/                   migrations
tests/                     pytest suite
```

## Data model

`users, candidates, candidate_cvs, skills, candidate_skills, candidate_experiences, candidate_educations, candidate_certifications, candidate_languages, candidate_projects, labels, candidate_labels, jobs, pipeline_stages, applications, candidate_activities, assessments, screening_results, embeddings, processing_jobs`.

Key relationships:

```
Candidate 1──* CandidateCV, CandidateSkill(→Skill), CandidateExperience, CandidateEducation,
              CandidateCertification, CandidateLanguage, CandidateProject, CandidateLabel(→Label),
              Application(→Job), Assessment, ScreeningResult, CandidateActivity
Candidate 1──1 CandidateEmbedding (pgvector)
Job       1──* PipelineStage, Application, ScreeningResult
```

Notable design choices:

- **`candidate_activities`** is an append-only event log — the single source of truth for a candidate's history timeline (uploads, screenings, stage changes, assessments, label changes, merges).
- **Merge never deletes.** `merge_service.merge_candidates` re-points the source candidate's CVs/skills/labels/applications/assessments/screening results/activity history onto the target, backfills any blank scalar fields on the target, and sets `source.merged_into_id = target.id`. The source row stays in the database (with its own `MERGED_AWAY` activity entry) — nothing is silently deleted.
- **`processing_jobs`** decouples "a file was uploaded" from "a candidate exists" so the frontend can show live UPLOADING → PARSING → PROCESSING → INDEXING → COMPLETED/FAILED status while a `BackgroundTasks` job runs, and so failed uploads can be retried without re-uploading the file.
- **Duplicate detection** (`duplicate_detection.find_duplicate`) matches on normalized email, then normalized phone, then normalized full name, against non-merged candidates. When the upload pipeline finds a match it does **not** silently create a second profile — it attaches the new CV (deduping any repeated experience/education/skill entries) to the existing candidate and logs a `CV_UPLOADED` (duplicate) activity. The separate `POST /candidates/{id}/merge` endpoint handles the general "these two existing profiles are the same person" case, for when a recruiter spots a duplicate manually in the Talent Pool.
- **`CandidateCV.extraction_method`** (`"text"` or `"ocr"`) records whether the file's text came from a normal text layer or from OCR, so the frontend/recruiter can see when a profile was built from a scanned image and might need a manual sanity check.

## AI abstraction details

### CVParser

```python
class CVParser(ABC):
    def parse(self, raw_text: str) -> ParsedCV: ...

RuleBasedCVParser   # regex/heuristics: section detection, date-range parsing, skill vocabulary matching
LLMCVParser         # builds a JSON-schema prompt (app/prompts/cv_extraction.py), calls LLMService,
                    # validates with Pydantic, retries up to 2x, falls back to RuleBasedCVParser on repeated failure
```

`get_cv_parser()` (factory) returns `RuleBasedCVParser` unless a real LLM key is configured (`has_configured_llm_keys()`), in which case it returns `LLMCVParser` wired to whichever provider(s) are configured (see rotation below).

### LLMService / EmbeddingService

Both are one-method interfaces (`complete(system, user) -> str`, `embed(text) -> list[float]`) so swapping providers never touches a caller. `LLMService` also has an optional `complete_vision(system, user, image_bytes, mime_type) -> str` for the OCR fallback path (implemented by `OpenAILLMService` and `GeminiLLMService`; the base default raises `NotImplementedError`). `MockLLMService` is not a stub — it deterministically parses the structured prompt text (built by `app/prompts/*`) and computes a real skill-overlap/experience-match score, so the screening/recommendation logic is exercised identically in mock and real modes. `MockEmbeddingService` uses the hashing trick (stable SHA-256-based feature hashing with adjacent-token bigrams) to produce a deterministic 384-dim vector — texts sharing vocabulary land closer together in cosine space, which is enough to demonstrate real semantic search without any ML runtime dependency.

### Multi-provider key rotation

`app/services/ai_common/key_pool.py` defines `ProviderKey` (provider name + api key + model) and `KeyPool`, a small round-robin-with-cooldown pool: `acquire_order()` returns every key once, healthy keys first, cooling-down keys last; `mark_failure`/`mark_success` manage the cooldown. It knows nothing about HTTP or any specific provider — it's pure bookkeeping, which is what makes it independently unit-testable (`tests/test_key_pool.py`) without any network mocking.

`RotatingLLMService` and `RotatingEmbeddingService` (in `llm/rotating_service.py` / `embedding/rotating_service.py`) wrap a `KeyPool`: each call walks `acquire_order()`, builds the concrete provider service for that key (`OpenAILLMService`/`GeminiLLMService`/etc.), and on any exception marks that key failed and moves to the next — which, when the pool spans providers, means a request can transparently fail over from OpenAI to Gemini mid-call. `llm/factory.get_llm_service()` builds the pool from the *effective* config (`core/runtime_config.get_ai_config()` — see below), filtered by `LLM_PROVIDER` (`"auto"` includes both providers; `"openai"`/`"gemini"` pins to one; `"mock"` skips the pool entirely). Embeddings deliberately do **not** allow a pool to mix providers — OpenAI (1536-dim) and Gemini (768-dim) vectors can't share one pgvector column — so `embedding/factory.get_embedding_service()`'s `"auto"` just picks one provider (preferring OpenAI) and rotates only within it; it also logs a warning if the resolved service's `dimensions` don't match `settings.EMBEDDING_DIM`.

### Admin-configurable settings (hot-swap, no restart)

`app/core/config.Settings` (loaded once from `.env`/env vars at process start, immutable in practice) is the *default* AI configuration. Sitting in front of it, `app/core/runtime_config.py` holds a small in-process `AIConfig` — llm/embedding/ocr provider choice, keys, models — that every factory (`llm/factory.py`, `embedding/factory.py`, `ocr/factory.py`, `cv_parser/factory.py`) reads via `get_ai_config()` instead of touching `Settings` directly. `apply_db_overrides(row)` recomputes that `AIConfig` from `Settings` merged with a `SystemSettings` DB row (any field left `NULL` in the row falls back to the env value) and clears the `@lru_cache` on all four factories, so the very next call rebuilds with the new provider/keys.

This is what makes **Settings → AI providers** in the frontend (Admin only; `api/v1/settings.py`, `services/settings/settings_service.py`) apply instantly with no container restart: `PUT /api/settings/ai` writes the row and calls `apply_db_overrides` in the same request. `apply_db_overrides(None)` (no row) is also called once at app startup (`main.py`'s startup event) to establish the baseline from `.env` alone. API keys are encrypted before being stored (`app/core/crypto.py`, Fernet, key derived from `ENCRYPTION_KEY`/`JWT_SECRET`) and the API only ever returns a masked preview (`****abcd`) — never the plaintext — see `mask_secret`/`AISettingsOut`. A `POST /api/settings/ai/test` endpoint makes one real minimal completion call so an admin can verify a key works *before* saving it.

This whole mechanism is single-process by design (see README's "Scaling constraint") — it's plain in-memory state, deliberately not a distributed cache, because CV processing (`BackgroundTasks`) already runs in this same process.

### OCR (scanned CV support)

`app/services/ocr/`: `OCRService.extract_text(image_bytes, mime_type) -> str`, implemented by:

- `TesseractOCRService` — the default, offline path (`pytesseract` + the `tesseract-ocr` binary, English + Vietnamese language packs).
- `LLMVisionOCRService` — calls `LLMService.complete_vision(...)` with a transcription prompt (`app/prompts/ocr.py`), so it automatically benefits from the same rotating key pool/failover as text completions.
- `HybridOCRService` — the `OCR_PROVIDER=auto` default: runs Tesseract first, and only calls the LLM-vision fallback if the result is shorter than `OCR_MIN_TEXT_LENGTH` *and* a real LLM key is configured, keeping whichever result is longer.

`app/services/cv_parser/extractors.py` uses this for two cases: a `.png`/`.jpg` upload goes straight to OCR; a `.pdf` upload first tries `pypdf`'s normal text-layer extraction, and only falls back to rasterizing each page (`pdf2image`/Poppler, capped at `OCR_MAX_PAGES`) and OCR'ing them if the text layer came back under `OCR_MIN_TEXT_LENGTH` characters — the classic signature of a scanned-and-saved-as-PDF resume. `extract_text()` returns `(text, "text" | "ocr")`, and the worker stores that on `CandidateCV.extraction_method`.

### Screening

`ScreeningService.screen(db, job, candidate)`:
1. Builds a prompt from `app/prompts/screening.py` (explicitly instructs the model to ignore protected attributes).
2. Calls `LLMService.complete(...)`.
3. Parses the response as JSON and validates it against `ScreeningLLMOutput` (Pydantic) — retries (LLM call + reparse) up to 2 extra times on invalid JSON/schema before raising.
4. Persists a `ScreeningResult`, updates `candidate.ai_score`, and logs an `AI_SCREENING` activity.

### Search

`SearchService` composes three swappable pieces:
- `KeywordSearch` — parses the boolean DSL (`AND`/`OR`/`-exclude`/quoted phrases) into OR-groups of AND-terms, and evaluates them against a per-candidate text document (name, title, summary, skills, experience/education text).
- `SemanticSearch` — embeds the query and ranks candidates by pgvector cosine similarity (`CandidateEmbedding.vector.cosine_distance(...)`), computed in SQL.
- `HybridSearch` — weighted combination of the two scores for relevance sorting.

Filters (skills/location/labels/experience/AI score) are pushed down into SQL; the boolean keyword match runs in Python over the filtered set — a deliberate simplicity trade-off documented in the README's known limitations (would move to Postgres full-text search or Elasticsearch/OpenSearch at much larger scale, without changing the `SearchService` interface).

### Recommendations ("Find candidates for this job")

`RecommendationService.find_candidates_for_job` combines, per candidate: keyword relevance against the job text, semantic similarity (embeddings), required/preferred skill match ratio, years-of-experience ratio, and the latest AI screening score for that job (if one exists) — weighted and normalized to 0-100, with a human-readable explanation generated through the same `LLMService` abstraction (`app/prompts/explanation.py`).

## Security

- JWT bearer auth (`python-jose`), bcrypt password hashing (`passlib`).
- RBAC via a FastAPI dependency (`core/deps.require_role`): `RecruiterOrAdmin` gates job/candidate/label mutations, CV upload, merge, and pipeline changes; `AdminOnly` additionally gates the AI Settings endpoints; any authenticated role (including `HIRING_MANAGER`) can view candidates/jobs/dashboard and add assessments, matching the spec's role matrix.
- File upload validation: extension allowlist (`.pdf`/`.docx`/`.png`/`.jpg`), a max size check, and a magic-byte check (`utils/file_storage.validate_file_content`) confirming the actual content matches the claimed extension before it ever reaches pypdf/python-docx/PIL — all before anything touches disk.
- AI provider API keys saved via the Settings UI are encrypted at rest (`core/crypto.py`, Fernet) and only ever returned to clients as a masked preview.
- Login is rate-limited per IP (`core/rate_limit.py`); a global security-headers middleware (`main.py`) adds `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and (in production) `Strict-Transport-Security` to every response.
- `GET /health` checks live Postgres connectivity (not just process liveness) and returns 503 when the DB is unreachable, for use with container/orchestrator health probes.
- Containers run as non-root (see README's "Production deployment"); a startup check warns loudly if `JWT_SECRET` is still the dev placeholder while `ENVIRONMENT=production`.
- Structured logging with `exc_info=True` on all unexpected errors; a global FastAPI exception handler prevents raw tracebacks from leaking to clients.

## Frontend architecture

See `frontend/src/` — router + layout in `app/`, a small hand-built Tailwind component kit in `components/ui/` (no shadcn CLI dependency), one folder per feature area under `features/` (talent-pool, candidates, jobs, pipeline, assessments, labels, dashboard, auth), and a typed API client + TanStack Query hooks under `services/`.
