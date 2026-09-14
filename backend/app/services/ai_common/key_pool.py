"""Generic rotate-and-fail-over pool of (provider, api_key) credentials.

Shared by the LLM and embedding rotating services so both "rotate between
multiple keys of one provider" and "rotate between providers (OpenAI/Gemini)"
go through the exact same, independently testable logic.
"""

import logging
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderKey:
    provider: str  # "openai" | "gemini"
    api_key: str
    model: str

    @property
    def id(self) -> str:
        # last 4 chars only — never log/expose a full API key
        return f"{self.provider}:{self.model}:...{self.api_key[-4:]}"


class AllKeysExhaustedError(RuntimeError):
    pass


class KeyPool:
    """Round-robins across healthy keys; a key that fails is put on a cooldown
    timer instead of being removed, so it's retried automatically once the
    cooldown expires (e.g. a per-minute rate limit resets)."""

    def __init__(self, keys: list[ProviderKey], cooldown_seconds: int | None = None) -> None:
        if not keys:
            raise ValueError("KeyPool requires at least one key")
        self._keys = keys
        self._cooldown_seconds = cooldown_seconds if cooldown_seconds is not None else settings.KEY_COOLDOWN_SECONDS
        self._cooldown_until: dict[str, float] = {}
        self._next_index = 0
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._keys)

    def _is_available(self, key: ProviderKey) -> bool:
        return time.monotonic() >= self._cooldown_until.get(key.id, 0.0)

    def acquire_order(self) -> list[ProviderKey]:
        """Returns every key once, starting from the next round-robin
        position, healthy keys first, then cooling-down keys as a last resort
        (better to retry a cooling key than to fail the whole request)."""
        with self._lock:
            start = self._next_index
            self._next_index = (self._next_index + 1) % len(self._keys)
            ordered = self._keys[start:] + self._keys[:start]
        healthy = [k for k in ordered if self._is_available(k)]
        cooling = [k for k in ordered if not self._is_available(k)]
        return healthy + cooling

    def mark_failure(self, key: ProviderKey) -> None:
        with self._lock:
            self._cooldown_until[key.id] = time.monotonic() + self._cooldown_seconds
        logger.warning("AI provider key %s failed, cooling down for %ss", key.id, self._cooldown_seconds)

    def mark_success(self, key: ProviderKey) -> None:
        with self._lock:
            self._cooldown_until.pop(key.id, None)


def build_pool(
    provider_filter: str,
    openai_keys: Sequence[str],
    openai_model: str,
    gemini_keys: Sequence[str],
    gemini_model: str,
) -> KeyPool | None:
    """provider_filter: 'openai' | 'gemini' | 'auto' — which provider(s) to include.

    Pure function of its arguments (no direct settings/DB access) so the
    caller decides where the keys come from — static .env config by default,
    or the admin Settings UI's DB-backed overrides (see core/runtime_config.py).
    """
    keys: list[ProviderKey] = []
    if provider_filter in ("openai", "auto"):
        keys += [ProviderKey("openai", k, openai_model) for k in openai_keys]
    if provider_filter in ("gemini", "auto"):
        keys += [ProviderKey("gemini", k, gemini_model) for k in gemini_keys]
    if not keys:
        return None
    return KeyPool(keys)
