from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemSettings(Base):
    """Singleton row (id is always 1) holding admin-editable overrides for the
    AI provider configuration. Anything left NULL here falls back to the
    corresponding backend/.env value — see app/core/runtime_config.py. This
    lets an admin switch LLM/embedding/OCR providers or rotate API keys from
    the UI, live, without editing files or restarting the container.

    API keys are stored encrypted (see app/core/crypto.py) — never in
    plaintext — and are never returned in full by the API (masked to the
    last 4 characters)."""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    embedding_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ocr_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)

    openai_api_keys_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    openai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    gemini_api_keys_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    gemini_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gemini_embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
