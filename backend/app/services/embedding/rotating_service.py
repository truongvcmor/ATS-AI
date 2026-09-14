import logging

from app.services.ai_common.key_pool import AllKeysExhaustedError, KeyPool, ProviderKey
from app.services.embedding.base import EmbeddingService

logger = logging.getLogger(__name__)


def _build_provider_service(key: ProviderKey) -> EmbeddingService:
    if key.provider == "openai":
        from app.services.embedding.openai_service import OpenAIEmbeddingService

        return OpenAIEmbeddingService(api_key=key.api_key, model=key.model)
    if key.provider == "gemini":
        from app.services.embedding.gemini_service import GeminiEmbeddingService

        return GeminiEmbeddingService(api_key=key.api_key, model=key.model)
    raise ValueError(f"Unknown embedding provider: {key.provider}")


class RotatingEmbeddingService(EmbeddingService):
    """Rotates across multiple keys of a *single* embedding provider (mixing
    providers here would mix vector dimensions in the same pgvector column,
    which breaks similarity search — see EMBEDDING_PROVIDER=auto in
    app/services/embedding/factory.py for how the provider is chosen)."""

    def __init__(self, pool: KeyPool) -> None:
        self._pool = pool
        # every key in the pool is the same provider/model, so this is safe:
        self._reference = _build_provider_service(pool.acquire_order()[0])

    @property
    def model_name(self) -> str:
        return self._reference.model_name

    @property
    def dimensions(self) -> int:
        return self._reference.dimensions

    def embed(self, text: str) -> list[float]:
        last_error: Exception | None = None
        for key in self._pool.acquire_order():
            service = _build_provider_service(key)
            try:
                result = service.embed(text)
                self._pool.mark_success(key)
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self._pool.mark_failure(key)
                logger.warning("Embedding call via %s failed, trying next key: %s", key.id, exc)
        raise AllKeysExhaustedError("All configured embedding keys failed") from last_error
