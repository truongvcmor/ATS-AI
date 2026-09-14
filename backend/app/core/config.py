from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "ATS Talent Pool"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+psycopg2://ats:ats@localhost:5433/ats"

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Encrypts API keys saved via the admin Settings UI before they're stored
    # in the database (see app/core/crypto.py). Falls back to deriving a key
    # from JWT_SECRET if unset — fine for a quick start, but set a dedicated
    # ENCRYPTION_KEY in production so rotating JWT_SECRET doesn't also break
    # decryption of already-stored provider API keys.
    ENCRYPTION_KEY: str | None = None

    # AI providers. Everything defaults to a mock/rule-based implementation so
    # the product works fully with zero external API keys.
    #
    # "auto" rotates across every key configured below (OpenAI + Gemini,
    # each of which can have multiple keys) with automatic failover on
    # rate-limit/auth/server errors. "openai"/"gemini" pin to just that
    # provider's key pool (still rotating across multiple keys if given).
    # "mock" always forces the deterministic mock, even if keys are set.
    LLM_PROVIDER: Literal["mock", "openai", "gemini", "auto"] = "mock"
    EMBEDDING_PROVIDER: Literal["mock", "openai", "gemini", "auto"] = "mock"

    # Single-key form (kept for backwards compatibility) and multi-key form
    # (comma-separated) — both are merged into one pool per provider.
    OPENAI_API_KEY: str | None = None
    OPENAI_API_KEYS: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    GEMINI_API_KEY: str | None = None
    GEMINI_API_KEYS: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIM: int = 384

    # How long a key is skipped after a retriable failure (rate limit, 5xx,
    # network error) before it's tried again.
    KEY_COOLDOWN_SECONDS: int = 60

    # CV scanning / OCR. "tesseract" is the free/offline default; "llm_vision"
    # sends the page image to a vision-capable model from the pool above
    # (only usable when real LLM keys are configured); "auto" tries Tesseract
    # first and only falls back to llm_vision if the result looks too short
    # AND a real LLM is configured.
    OCR_PROVIDER: Literal["tesseract", "llm_vision", "auto"] = "auto"
    OCR_MIN_TEXT_LENGTH: int = 40
    OCR_MAX_PAGES: int = 5

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_CV_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx", ".png", ".jpg", ".jpeg")

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60

    def openai_keys(self) -> list[str]:
        return _merge_keys(self.OPENAI_API_KEY, self.OPENAI_API_KEYS)

    def gemini_keys(self) -> list[str]:
        return _merge_keys(self.GEMINI_API_KEY, self.GEMINI_API_KEYS)


def _merge_keys(single: str | None, multi: str | None) -> list[str]:
    keys: list[str] = []
    if single:
        keys.append(single.strip())
    if multi:
        keys.extend(k.strip() for k in multi.split(",") if k.strip())
    # de-dupe while preserving order
    seen: set[str] = set()
    unique = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
