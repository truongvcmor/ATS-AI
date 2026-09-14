"""In-process, hot-swappable AI provider configuration.

CV processing runs via FastAPI `BackgroundTasks` in the same process as the
API server (there's no separate Celery worker), so a simple module-level
cache is enough to let an admin change the LLM/embedding/OCR provider (or
rotate an API key) from the Settings UI and have it take effect on the very
next request/upload — no restart, no need to thread a DB session through
every AI call site.

`apply_db_overrides()` is called once at app startup (see main.py) and again
every time the admin saves new settings (see api/v1/settings.py). Any field
left NULL in the DB row falls back to the corresponding backend/.env value.
"""

import logging
import threading
from dataclasses import dataclass, replace

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIConfig:
    llm_provider: str
    embedding_provider: str
    ocr_provider: str
    openai_keys: tuple[str, ...]
    openai_model: str
    gemini_keys: tuple[str, ...]
    gemini_model: str
    embedding_model: str
    gemini_embedding_model: str


def _from_env() -> AIConfig:
    return AIConfig(
        llm_provider=settings.LLM_PROVIDER,
        embedding_provider=settings.EMBEDDING_PROVIDER,
        ocr_provider=settings.OCR_PROVIDER,
        openai_keys=tuple(settings.openai_keys()),
        openai_model=settings.OPENAI_MODEL,
        gemini_keys=tuple(settings.gemini_keys()),
        gemini_model=settings.GEMINI_MODEL,
        embedding_model=settings.EMBEDDING_MODEL,
        gemini_embedding_model=settings.GEMINI_EMBEDDING_MODEL,
    )


_lock = threading.Lock()
_current: AIConfig = _from_env()


def get_ai_config() -> AIConfig:
    with _lock:
        return _current


def apply_db_overrides(row: "SystemSettings | None") -> None:  # noqa: F821 (typed as string to avoid a hard import)
    """Recompute the effective config from env defaults + DB overrides, and
    drop every cached provider-service singleton so the next call to
    get_llm_service()/get_embedding_service()/get_ocr_service()/get_cv_parser()
    rebuilds with the new configuration."""
    global _current
    base = _from_env()

    if row is not None:
        from app.core.crypto import decrypt_secret

        openai_keys = _decrypt_keys(row.openai_api_keys_encrypted, decrypt_secret) or base.openai_keys
        gemini_keys = _decrypt_keys(row.gemini_api_keys_encrypted, decrypt_secret) or base.gemini_keys
        resolved = AIConfig(
            llm_provider=row.llm_provider or base.llm_provider,
            embedding_provider=row.embedding_provider or base.embedding_provider,
            ocr_provider=row.ocr_provider or base.ocr_provider,
            openai_keys=openai_keys,
            openai_model=row.openai_model or base.openai_model,
            gemini_keys=gemini_keys,
            gemini_model=row.gemini_model or base.gemini_model,
            embedding_model=row.embedding_model or base.embedding_model,
            gemini_embedding_model=row.gemini_embedding_model or base.gemini_embedding_model,
        )
    else:
        resolved = base

    with _lock:
        _current = resolved

    _clear_provider_caches()
    logger.info(
        "AI config applied: llm=%s embedding=%s ocr=%s (source=%s)",
        resolved.llm_provider,
        resolved.embedding_provider,
        resolved.ocr_provider,
        "db+env" if row is not None else "env",
    )


def _decrypt_keys(encrypted_blob: str | None, decrypt) -> tuple[str, ...]:
    if not encrypted_blob:
        return ()
    plaintext = decrypt(encrypted_blob)
    if not plaintext:
        return ()
    return tuple(k.strip() for k in plaintext.split(",") if k.strip())


def _clear_provider_caches() -> None:
    from app.services.cv_parser.factory import get_cv_parser
    from app.services.embedding.factory import get_embedding_service
    from app.services.llm.factory import get_llm_service
    from app.services.ocr.factory import get_ocr_service

    get_llm_service.cache_clear()
    get_embedding_service.cache_clear()
    get_ocr_service.cache_clear()
    get_cv_parser.cache_clear()
