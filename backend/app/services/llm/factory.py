from functools import lru_cache

from app.core.runtime_config import get_ai_config
from app.services.ai_common.key_pool import build_pool
from app.services.llm.base import LLMService
from app.services.llm.mock import MockLLMService


def has_configured_llm_keys() -> bool:
    cfg = get_ai_config()
    if cfg.llm_provider == "mock":
        return False
    return build_pool(cfg.llm_provider, cfg.openai_keys, cfg.openai_model, cfg.gemini_keys, cfg.gemini_model) is not None


@lru_cache
def get_llm_service() -> LLMService:
    cfg = get_ai_config()
    if cfg.llm_provider != "mock":
        pool = build_pool(cfg.llm_provider, cfg.openai_keys, cfg.openai_model, cfg.gemini_keys, cfg.gemini_model)
        if pool is not None:
            from app.services.llm.rotating_service import RotatingLLMService

            return RotatingLLMService(pool)
    return MockLLMService()
