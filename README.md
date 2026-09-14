# ATS Talent Pool — AI-Powered E-Hiring Platform

A working MVP of an ATS / E-hiring platform that turns a pile of CVs into a searchable, reusable **Talent Pool**: upload CVs, get them parsed automatically, screen candidates with AI against job requirements, search and filter the pool (keyword + semantic), run a Kanban recruitment pipeline, and keep a full history of every candidate so they can be rediscovered for future roles.

## Product overview

The core workflow:

```
Upload CV → Parse → Candidate Profile → AI Screening → Talent Pool → Search/Filter →
Recruitment Pipeline → Assessment/History → Reuse candidate for future jobs
```

The main product principle: a CV is uploaded **once**, and the resulting candidate profile stays searchable and reusable for every future job — not just the one it was uploaded for.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full breakdown. In short:

```
Frontend (React/TS)  →  FastAPI  →  Service layer  →  Repository/ORM  →  PostgreSQL + pgvector
                                        │
                                        └── AI layer: CVParser / LLMService / EmbeddingService
                                            (Mock/rule-based by default, OpenAI-backed when configured)
```

- **Backend**: Python, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, PostgreSQL + pgvector.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, recharts, dnd-kit.
- **AI**: pluggable `LLMService` / `EmbeddingService` / `CVParser` abstractions. Default provider is a deterministic **mock/rule-based** implementation — the whole product works with zero API keys. Configure OpenAI and/or Gemini keys to switch to real models; multiple keys/providers rotate automatically with failover (see "Multi-provider AI key rotation" below).
- **CV scanning (OCR)**: image CVs (`.png`/`.jpg`) and scanned/no-text-layer PDFs are automatically run through OCR (Tesseract by default, optional LLM-vision fallback) before parsing — see "Scanned CV / OCR support" below.
- **Background processing**: CV parsing/embedding runs via FastAPI `BackgroundTasks` (no Redis/Celery needed for this MVP scale) and is tracked in a `processing_jobs` table the frontend polls.

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI + Uvicorn |
| ORM / migrations | SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL 16 + pgvector |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| CV parsing | pypdf (PDF), python-docx (DOCX), regex/heuristic rule-based parser |
| AI | Mock (rule-based) by default; OpenAI chat + embeddings when configured |
| Frontend | React + TypeScript + Vite + Tailwind + TanStack Query + React Router + recharts + dnd-kit |
| Tests | pytest + httpx (backend) |
| Infra | Docker Compose (postgres, backend, frontend) |

## Running with Docker Compose (recommended)

Requires Docker + the Compose plugin.

```bash
cp backend/.env.example backend/.env   # defaults already work out of the box (mock AI, dev JWT secret)
docker compose up --build
```

Services (host ports chosen to avoid clashing with other local projects):

- Frontend: http://localhost:5173
- Backend API: http://localhost:8080 (docs at http://localhost:8080/docs)
- Postgres: localhost:5433 (user/pass/db: `ats`/`ats`/`ats`)

The backend container runs `alembic upgrade head` automatically on start, so the schema is always up to date.

### Seed data

Populate the database with ~30 realistic candidates (uploaded through the real parsing pipeline), 5 jobs, 10 labels, applications, AI screenings, pipeline movement, and assessments:

```bash
docker compose exec backend python -m app.seed
```

This also creates three demo users:

| Email | Password | Role |
|---|---|---|
| admin@ats.com | admin123 | ADMIN |
| recruiter@ats.com | recruiter123 | RECRUITER |
| manager@ats.com | manager123 | HIRING_MANAGER |

### Sharing over your LAN (e.g. for a demo)

By default the stack is wired for `localhost` only — fine for solo dev, but the frontend bundle bakes in `http://localhost:8080/api` as the backend URL, which breaks for anyone opening it from another device (their browser would try *their own* localhost). To share it with teammates on the same Wi-Fi/LAN:

1. Find your machine's LAN IP: `hostname -I` (Linux) or `ipconfig` (Windows) — e.g. `192.168.1.50`.
2. Create a **repo-root** `.env` (see `.env.example`) with:
   ```env
   LAN_HOST=192.168.1.50
   ```
3. `docker compose up -d` (no rebuild needed — this only changes runtime env vars: the frontend's API URL and the backend's allowed CORS origins both key off `LAN_HOST`).
4. Share either URL with teammates on the same network:
   - `http://192.168.1.50:5173` (plain IP), or
   - `http://192.168.1.50.nip.io:5173` — a real, no-setup-needed "domain" ([nip.io](https://nip.io) is a free wildcard DNS service that resolves `<any-ip>.nip.io` straight back to that IP; traffic still goes directly over your LAN, nip.io is only used for the DNS lookup).

If it's unreachable from another device, the host's firewall is the usual culprit — allow the two ports, e.g. on Ubuntu: `sudo ufw allow 5173/tcp && sudo ufw allow 8080/tcp`.

Leave `LAN_HOST` unset (or delete the root `.env`) to go back to localhost-only.

## Running locally without Docker

Backend (needs a local Postgres with the `vector` extension available — easiest is still to run just the `postgres` service via Compose and point at `localhost:5433`):

```bash
docker compose up -d postgres
cd backend
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL already points at localhost:5433
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000/api if running the backend locally on 8000
npm run dev
```

## Environment variables

All in `backend/.env` (see `backend/.env.example`):

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy Postgres URL | `postgresql+psycopg2://ats:ats@localhost:5433/ats` |
| `JWT_SECRET` | HMAC secret for access tokens | dev placeholder — change for anything real |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime | 1440 |
| `LLM_PROVIDER` / `EMBEDDING_PROVIDER` | `mock` \| `openai` \| `gemini` \| `auto` | `mock` |
| `OPENAI_API_KEY` / `OPENAI_API_KEYS` / `OPENAI_MODEL` | single key / comma-separated multiple keys / model | empty / empty / `gpt-4o-mini` |
| `GEMINI_API_KEY` / `GEMINI_API_KEYS` / `GEMINI_MODEL` | same, for Gemini | empty / empty / `gemini-1.5-flash` |
| `EMBEDDING_MODEL` / `GEMINI_EMBEDDING_MODEL` / `EMBEDDING_DIM` | embedding models + pgvector column width | `text-embedding-3-small` / `text-embedding-004` / 384 |
| `KEY_COOLDOWN_SECONDS` | how long a failed key is skipped before retry | 60 |
| `OCR_PROVIDER` | `tesseract` \| `llm_vision` \| `auto` | `auto` |
| `OCR_MIN_TEXT_LENGTH` / `OCR_MAX_PAGES` | scanned-PDF detection threshold / page cap | 40 / 5 |
| `UPLOAD_DIR` | where CV files are stored | `uploads` |
| `MAX_UPLOAD_SIZE` | upload size limit in bytes | 10 MB |

Never commit real API keys — `.env` is gitignored.

## Database migrations

```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
docker compose exec backend alembic upgrade head
```

## Running tests

```bash
docker compose exec -e DATABASE_URL=postgresql+psycopg2://ats:ats@postgres:5432/ats_test backend pytest
```

The test suite creates/truncates a separate `ats_test` database automatically — it never touches your dev data. Covers: auth, candidate CRUD, CV upload/parsing, duplicate detection, merge, labels, job CRUD, AI screening, recommendations, pipeline stage transitions, assessments, keyword/semantic search, RBAC, scanned-CV OCR, the AI provider key-rotation/failover logic, and a full end-to-end recruitment flow.

## AI configuration

By design, **the product works fully with no AI provider configured** — `CVParser`, `LLMService`, and `EmbeddingService` all default to deterministic, dependency-free implementations (`RuleBasedCVParser`, `MockLLMService`, `MockEmbeddingService`). To use real models instead, set one or more API keys:

```env
LLM_PROVIDER=auto
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

No other code changes are required — every call site goes through the abstract `LLMService`/`EmbeddingService`/`CVParser` interfaces (see [ARCHITECTURE.md](ARCHITECTURE.md)).

Fairness: the screening prompt (`backend/app/prompts/screening.py`) explicitly instructs the model to ignore gender, age, race, religion, marital status, nationality, health, and appearance, and every screening result is labeled in the UI as an AI-generated recommendation for the recruiter to review — not an automatic decision.

### Multi-provider AI key rotation

Set `LLM_PROVIDER=auto` (or `openai`/`gemini` to pin to one) and supply one or more keys per provider — either a single `OPENAI_API_KEY` / `GEMINI_API_KEY`, or several comma-separated in `OPENAI_API_KEYS` / `GEMINI_API_KEYS` (both forms can be combined; they're merged into one pool). Every LLM call:

1. Picks the next key round-robin.
2. On failure (rate limit, auth error, timeout, 5xx) puts that key on a cooldown (`KEY_COOLDOWN_SECONDS`, default 60s) and immediately retries with the **next** key — which, with `LLM_PROVIDER=auto`, can mean **failing over from OpenAI to Gemini** (or vice versa) transparently, mid-request.
3. Only raises if every configured key has failed.

This is implemented once in `app/services/ai_common/key_pool.py` (`KeyPool`) and reused by both `RotatingLLMService` and `RotatingEmbeddingService` — see [ARCHITECTURE.md](ARCHITECTURE.md) for how it plugs into the existing provider abstraction. Embeddings intentionally do **not** mix providers within one pool (OpenAI and Gemini produce different vector dimensions, which would corrupt the single pgvector column) — `EMBEDDING_PROVIDER=auto` there just auto-selects whichever single provider has keys configured, still rotating across multiple keys of that provider.

## Scanned CV / OCR support

Image files (`.png`, `.jpg`/`.jpeg`) and scanned PDFs (a PDF with no real text layer — pypdf extracts under `OCR_MIN_TEXT_LENGTH` characters) are automatically routed through OCR before parsing, so a candidate can upload a phone photo or a flatbed scan of a paper CV just like a normal PDF/DOCX. Each `CandidateCV` record's `extraction_method` field (`text` or `ocr`) reports which path was used.

`OCR_PROVIDER` controls the method:

- `tesseract` (free, offline, default fallback) — the Tesseract binary via `pytesseract`, with English + Vietnamese language packs installed in the Docker image.
- `llm_vision` — sends the page image to a vision-capable model from the same rotating key pool above (`gpt-4o-mini` / `gemini-1.5-flash` both support image input); only usable when a real key is configured.
- `auto` (default) — try Tesseract first; if the result looks too short (`OCR_MIN_TEXT_LENGTH`) **and** a real LLM key is configured, retry with `llm_vision` and keep whichever result is longer.

A scanned PDF's pages are rasterized with `pdf2image`/Poppler (capped at `OCR_MAX_PAGES` pages) before each page image is OCR'd the same way as a standalone image upload.

## Known limitations

- No Celery/Redis — CV processing runs via FastAPI `BackgroundTasks`, which is fine at MVP scale but not horizontally scalable across multiple backend replicas.
- Vector search uses pgvector with a default 384-dim mock embedding; switching to a real embedding provider (OpenAI=1536 dims, Gemini=768 dims) requires a migration to resize the `embeddings.vector` column to match (`EMBEDDING_DIM` must equal the provider's actual output size).
- Keyword/boolean search filters candidates in Python after a bounded SQL prefetch rather than pushing full-text search into Postgres/Elasticsearch — fine for thousands of candidates, not millions.
- CV files are stored on local disk (a Docker volume), not S3/object storage.
- No audit log / data retention / consent tracking yet (the data model and merge-never-deletes behavior make these straightforward to add later).
- The rule-based CV parser is heuristic — it works well on reasonably-formatted English/Vietnamese resumes with recognizable section headers, and handles the PDF-specific quirks of pypdf text extraction (missing blank lines, mid-line wraps). It does **not** reliably parse fundamentally different layouts — multi-column skill-matrix tables, or documents in a language it doesn't have section-header aliases for (currently English + Vietnamese, with light Japanese support: it recognizes a handful of common Japanese section headers and a "romanized name in parentheses" pattern typical of Japan-market skill-sheets, but not full-document parsing). For any CV whose structure it can't confidently recognize, configure a real `LLM_PROVIDER` (OpenAI or Gemini) — `LLMCVParser` understands arbitrary layouts and languages far better than regex heuristics ever will, and is the recommended fix if you're seeing consistently poor extraction on a particular CV format/language.
- Key rotation state (cooldowns) is in-process memory — it resets on restart and isn't shared across multiple backend replicas; fine for a single instance, would need a shared store (e.g. Redis) to coordinate cooldowns across replicas.
- Tesseract OCR accuracy is decent but not perfect on low-quality photos (e.g. it occasionally confuses `I`/`l`); the `llm_vision` fallback is meaningfully more accurate when a real key is configured.

## Recommended next steps

- Wire a real OpenAI (or other provider) key for production-quality parsing/screening/embeddings.
- Add pgvector ANN indexing (`ivfflat`/`hnsw`) once the talent pool grows past a few thousand candidates.
- Move CV processing to Celery + Redis if you need multiple backend replicas.
- Add S3-compatible object storage for CV files.
- Add audit logging, data retention policies, and candidate data export/deletion workflows for full GDPR-style compliance.
