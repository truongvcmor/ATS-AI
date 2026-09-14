import logging

from app.services.ai_common.key_pool import AllKeysExhaustedError, KeyPool, ProviderKey
from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)


def _build_provider_service(key: ProviderKey) -> LLMService:
    if key.provider == "openai":
        from app.services.llm.openai_service import OpenAILLMService

        return OpenAILLMService(api_key=key.api_key, model=key.model)
    if key.provider == "gemini":
        from app.services.llm.gemini_service import GeminiLLMService

        return GeminiLLMService(api_key=key.api_key, model=key.model)
    raise ValueError(f"Unknown LLM provider: {key.provider}")


class RotatingLLMService(LLMService):
    """Rotates across every configured key — potentially spanning multiple
    providers (OpenAI, Gemini) — falling over to the next one whenever a
    call fails (rate limit, auth error, transient 5xx/network error). A
    failed key is put on a cooldown rather than dropped, so it's retried
    automatically once the cooldown window passes.
    """

    def __init__(self, pool: KeyPool) -> None:
        self._pool = pool

    def _run(self, call) -> str:
        last_error: Exception | None = None
        for key in self._pool.acquire_order():
            service = _build_provider_service(key)
            try:
                result = call(service)
                self._pool.mark_success(key)
                return result
            except Exception as exc:  # noqa: BLE001 - any provider failure triggers failover
                last_error = exc
                self._pool.mark_failure(key)
                logger.warning("LLM call via %s failed, trying next key: %s", key.id, exc)
        raise AllKeysExhaustedError("All configured LLM keys failed") from last_error

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self._run(lambda service: service.complete(system_prompt, user_prompt))

    def complete_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str) -> str:
        return self._run(lambda service: service.complete_vision(system_prompt, user_prompt, image_bytes, mime_type))
