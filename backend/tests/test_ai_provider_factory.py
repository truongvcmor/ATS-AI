import pytest

from app.core.config import settings
from app.core.runtime_config import apply_db_overrides
from app.services.embedding.factory import get_embedding_service
from app.services.embedding.mock import MockEmbeddingService
from app.services.embedding.rotating_service import RotatingEmbeddingService
from app.services.llm.factory import get_llm_service, has_configured_llm_keys
from app.services.llm.mock import MockLLMService
from app.services.llm.rotating_service import RotatingLLMService


def _sync():
    """Recompute the in-process AI config from the (test-mutated) env
    settings, as if no DB override exists — mirrors what apply_db_overrides
    does at app startup. Needed because the factories now read from
    core.runtime_config's cache rather than app.core.config.settings
    directly (that cache is what makes the admin Settings UI hot-swappable
    without a restart — see core/runtime_config.py)."""
    apply_db_overrides(None)


@pytest.fixture(autouse=True)
def _reset_caches():
    original = {
        "LLM_PROVIDER": settings.LLM_PROVIDER,
        "EMBEDDING_PROVIDER": settings.EMBEDDING_PROVIDER,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "OPENAI_API_KEYS": settings.OPENAI_API_KEYS,
        "GEMINI_API_KEY": settings.GEMINI_API_KEY,
        "GEMINI_API_KEYS": settings.GEMINI_API_KEYS,
    }
    yield
    for key, value in original.items():
        setattr(settings, key, value)
    _sync()


def test_defaults_to_mock_with_no_keys():
    settings.LLM_PROVIDER = "auto"
    settings.OPENAI_API_KEY = None
    settings.OPENAI_API_KEYS = None
    settings.GEMINI_API_KEY = None
    settings.GEMINI_API_KEYS = None
    _sync()
    assert isinstance(get_llm_service(), MockLLMService)
    assert has_configured_llm_keys() is False


def test_explicit_mock_wins_even_if_keys_are_set():
    settings.LLM_PROVIDER = "mock"
    settings.OPENAI_API_KEY = "sk-fake"
    _sync()
    assert isinstance(get_llm_service(), MockLLMService)


def test_single_openai_key_builds_rotating_service():
    settings.LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "sk-fake-key"
    settings.OPENAI_API_KEYS = None
    _sync()
    service = get_llm_service()
    assert isinstance(service, RotatingLLMService)


def test_auto_provider_pools_both_openai_and_gemini_keys():
    settings.LLM_PROVIDER = "auto"
    settings.OPENAI_API_KEY = "sk-fake-openai"
    settings.GEMINI_API_KEY = "fake-gemini-key"
    _sync()
    service = get_llm_service()
    assert isinstance(service, RotatingLLMService)
    assert len(service._pool) == 2


def test_embedding_auto_prefers_openai_when_both_configured_to_avoid_dimension_mixing():
    settings.EMBEDDING_PROVIDER = "auto"
    settings.OPENAI_API_KEY = "sk-fake-openai"
    settings.GEMINI_API_KEY = "fake-gemini-key"
    _sync()
    service = get_embedding_service()
    assert isinstance(service, RotatingEmbeddingService)
    assert service.model_name == settings.EMBEDDING_MODEL  # openai model, not gemini's


def test_embedding_falls_back_to_mock_without_keys():
    settings.EMBEDDING_PROVIDER = "auto"
    settings.OPENAI_API_KEY = None
    settings.OPENAI_API_KEYS = None
    settings.GEMINI_API_KEY = None
    settings.GEMINI_API_KEYS = None
    _sync()
    assert isinstance(get_embedding_service(), MockEmbeddingService)


def test_multiple_comma_separated_keys_are_merged():
    settings.LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "sk-single"
    settings.OPENAI_API_KEYS = "sk-two,sk-three"
    _sync()
    service = get_llm_service()
    assert len(service._pool) == 3
