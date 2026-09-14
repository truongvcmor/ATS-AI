import base64
import logging

import httpx

from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiLLMService(LLMService):
    """Thin wrapper over the Google Gemini generateContent API."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def _post(self, system_prompt: str, parts: list[dict]) -> str:
        url = f"{GEMINI_API_BASE}/{self._model}:generateContent?key={self._api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.2},
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except httpx.HTTPError:
            logger.error("Gemini completion request failed", exc_info=True)
            raise

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self._post(system_prompt, [{"text": user_prompt}])

    def complete_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        return self._post(
            system_prompt,
            [{"text": user_prompt}, {"inline_data": {"mime_type": mime_type, "data": b64}}],
        )
