import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from app.core.runtime_config import apply_db_overrides, get_ai_config
from app.models.system_settings import SystemSettings
from app.schemas.settings import AISettingsOut, AISettingsTestResult, AISettingsUpdate

SETTINGS_ROW_ID = 1


def get_or_create_row(db: Session) -> SystemSettings:
    row = db.get(SystemSettings, SETTINGS_ROW_ID)
    if row is None:
        row = SystemSettings(id=SETTINGS_ROW_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _mask_keys(encrypted_blob: str | None) -> list[str]:
    if not encrypted_blob:
        return []
    plaintext = decrypt_secret(encrypted_blob)
    if not plaintext:
        return []
    return [mask_secret(k) for k in plaintext.split(",") if k.strip()]


def build_settings_out(row: SystemSettings) -> AISettingsOut:
    cfg = get_ai_config()
    return AISettingsOut(
        llm_provider=cfg.llm_provider,
        embedding_provider=cfg.embedding_provider,
        ocr_provider=cfg.ocr_provider,
        openai_configured=bool(cfg.openai_keys),
        openai_keys_masked=_mask_keys(row.openai_api_keys_encrypted) or _mask_keys_from_env(settings.openai_keys()),
        openai_model=cfg.openai_model,
        openai_source="database" if row.openai_api_keys_encrypted else ("env" if settings.openai_keys() else "none"),
        gemini_configured=bool(cfg.gemini_keys),
        gemini_keys_masked=_mask_keys(row.gemini_api_keys_encrypted) or _mask_keys_from_env(settings.gemini_keys()),
        gemini_model=cfg.gemini_model,
        gemini_source="database" if row.gemini_api_keys_encrypted else ("env" if settings.gemini_keys() else "none"),
        embedding_model=cfg.embedding_model,
        gemini_embedding_model=cfg.gemini_embedding_model,
        embedding_dim=settings.EMBEDDING_DIM,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )


def _mask_keys_from_env(keys: list[str]) -> list[str]:
    return [mask_secret(k) for k in keys]


def update_settings(db: Session, payload: AISettingsUpdate, updated_by: str) -> SystemSettings:
    row = get_or_create_row(db)
    data = payload.model_dump(exclude_unset=True)

    if "openai_api_keys" in data:
        value = data.pop("openai_api_keys")
        row.openai_api_keys_encrypted = encrypt_secret(value) if value else None
    if "gemini_api_keys" in data:
        value = data.pop("gemini_api_keys")
        row.gemini_api_keys_encrypted = encrypt_secret(value) if value else None

    for field, value in data.items():
        setattr(row, field, value or None)

    row.updated_by = updated_by
    db.commit()
    db.refresh(row)

    apply_db_overrides(row)
    return row


def load_overrides_on_startup(db: Session) -> None:
    row = db.get(SystemSettings, SETTINGS_ROW_ID)
    apply_db_overrides(row)


def test_provider(provider: str, api_key: str | None, model: str | None) -> AISettingsTestResult:
    """Makes one minimal real API call to verify a key/provider actually
    works, without persisting anything — used by the Settings UI's "Test
    connection" button before an admin commits to saving a new key."""
    resolved_key = api_key
    if not resolved_key:
        cfg = get_ai_config()
        keys = cfg.openai_keys if provider == "openai" else cfg.gemini_keys
        resolved_key = keys[0] if keys else None
    if not resolved_key:
        return AISettingsTestResult(ok=False, message=f"No {provider} API key configured or provided to test.")

    if provider == "openai":
        from app.services.llm.openai_service import OpenAILLMService

        service = OpenAILLMService(api_key=resolved_key, model=model or get_ai_config().openai_model)
    else:
        from app.services.llm.gemini_service import GeminiLLMService

        service = GeminiLLMService(api_key=resolved_key, model=model or get_ai_config().gemini_model)

    start = time.monotonic()
    try:
        response = service.complete("Reply with exactly one word: OK", "OK")
        latency_ms = int((time.monotonic() - start) * 1000)
        if not response or not response.strip():
            return AISettingsTestResult(ok=False, message="Provider returned an empty response.", latency_ms=latency_ms)
        return AISettingsTestResult(ok=True, message="Connection successful.", latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001 — surfacing the failure reason to the admin is the point
        latency_ms = int((time.monotonic() - start) * 1000)
        return AISettingsTestResult(ok=False, message=f"{type(exc).__name__}: {exc}", latency_ms=latency_ms)
