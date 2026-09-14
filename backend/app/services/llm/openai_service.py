import base64
import logging

import httpx

from app.services.llm.base import LLMService

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class OpenAILLMService(LLMService):
    """Thin wrapper over the OpenAI chat completions API."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def _post(self, messages: list[dict]) -> str:
        payload = {"model": self._model, "messages": messages, "temperature": 0.2}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(OPENAI_CHAT_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPError:
            logger.error("OpenAI completion request failed", exc_info=True)
            raise

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self._post(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

    def complete_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        return self._post(
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                    ],
                },
            ]
        )
