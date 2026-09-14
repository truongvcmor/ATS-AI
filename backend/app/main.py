import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

if settings.ENVIRONMENT == "production" and settings.JWT_SECRET == "change-me-in-production":
    logger.warning(
        "JWT_SECRET is still the development placeholder while ENVIRONMENT=production. "
        "Set a strong, unique JWT_SECRET before exposing this instance — every existing "
        "login token would be forgeable otherwise."
    )

app = FastAPI(title=settings.APP_NAME, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if settings.ENVIRONMENT == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s", request.method, request.url, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(api_router)


@app.on_event("startup")
def load_ai_settings_overrides() -> None:
    # Import here (not at module load time) — app.models must already be
    # importable via Alembic/SQLAlchemy metadata, which happens as part of
    # normal app.services import chains; keeping this local avoids any
    # import-order surprises during app construction above.
    from app.services.settings.settings_service import load_overrides_on_startup

    db = SessionLocal()
    try:
        load_overrides_on_startup(db)
    except Exception:  # noqa: BLE001 — never fail startup over optional DB-backed AI overrides
        logger.error("Failed to load AI settings overrides from the database; using .env defaults", exc_info=True)
    finally:
        db.close()


@app.get("/health")
def health() -> JSONResponse:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        logger.error("Health check: database connection failed", exc_info=True)
        db_ok = False
    body = {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "unreachable"}
    return JSONResponse(status_code=200 if db_ok else 503, content=body)
