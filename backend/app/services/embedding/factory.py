import logging
from functools import lru_cache

from app.core.config import settings
from app.core.runtime_config import AIConfig, get_ai_config
from app.services.ai_common.key_pool import KeyPool, ProviderKey
from app.services.embedding.base import EmbeddingService
from app.services.embedding.mock import MockEmbeddingService

logger = logging.getLogger(__name__)


def _resolve_provider(cfg: AIConfig) -> str | None:
    """Embeddings can't mix providers in one pool (different dimensions would
    corrupt the pgvector column), so 'auto' just picks whichever provider has
    keys configured, preferring OpenAI, and still rotates across multiple
    keys *within* that provider."""
    provider = cfg.embedding_provider
    if provider == "mock":
        return None
    if provider != "auto":
        return provider
    if cfg.openai_keys:
        return "openai"
    if cfg.gemini_keys:
        return "gemini"
    return None


@lru_cache
def get_embedding_service() -> EmbeddingService:
    cfg = get_ai_config()
    provider = _resolve_provider(cfg)
    if provider == "openai" and cfg.openai_keys:
        pool = KeyPool([ProviderKey("openai", k, cfg.embedding_model) for k in cfg.openai_keys])
    elif provider == "gemini" and cfg.gemini_keys:
        pool = KeyPool([ProviderKey("gemini", k, cfg.gemini_embedding_model) for k in cfg.gemini_keys])
    else:
        return MockEmbeddingService(dimensions=settings.EMBEDDING_DIM)

    from app.services.embedding.rotating_service import RotatingEmbeddingService

    service = RotatingEmbeddingService(pool)
    if service.dimensions != settings.EMBEDDING_DIM:
        logger.warning(
            "EMBEDDING_DIM (%s) does not match the %s embedding model's actual dimensions (%s) — "
            "the embeddings.vector column must be migrated to match before real vector search will work.",
            settings.EMBEDDING_DIM,
            service.model_name,
            service.dimensions,
        )
    return service
