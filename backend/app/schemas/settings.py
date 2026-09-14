from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Source = Literal["database", "env", "none"]


class AISettingsUpdate(BaseModel):
    """Partial update — omit a field to leave it untouched. Send a field as
    `null` (or an empty string, for the API-key fields) to clear the DB
    override and fall back to the backend/.env value."""

    llm_provider: Literal["mock", "openai", "gemini", "auto"] | None = None
    embedding_provider: Literal["mock", "openai", "gemini", "auto"] | None = None
    ocr_provider: Literal["tesseract", "llm_vision", "auto"] | None = None
    openai_api_keys: str | None = None  # comma-separated
    openai_model: str | None = None
    gemini_api_keys: str | None = None
    gemini_model: str | None = None
    embedding_model: str | None = None
    gemini_embedding_model: str | None = None


class AISettingsOut(BaseModel):
    llm_provider: str
    embedding_provider: str
    ocr_provider: str

    openai_configured: bool
    openai_keys_masked: list[str]
    openai_model: str
    openai_source: Source

    gemini_configured: bool
    gemini_keys_masked: list[str]
    gemini_model: str
    gemini_source: Source

    embedding_model: str
    gemini_embedding_model: str
    embedding_dim: int  # informational only — changing it requires a DB migration, not editable here

    updated_at: datetime | None = None
    updated_by: str | None = None


class AISettingsTestRequest(BaseModel):
    provider: Literal["openai", "gemini"]
    # Optional: test a key before saving it. Omit to test the currently active key(s).
    api_key: str | None = None
    model: str | None = None


class AISettingsTestResult(BaseModel):
    ok: bool
    message: str
    latency_ms: int | None = None
