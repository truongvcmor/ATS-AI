import logging

import httpx

from app.services.embedding.base import EmbeddingService

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_MODEL_DIMENSIONS = {
    "text-embedding-004": 768,
}


class GeminiEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return _MODEL_DIMENSIONS.get(self._model, 768)

    def embed(self, text: str) -> list[float]:
        url = f"{GEMINI_API_BASE}/{self._model}:embedContent?key={self._api_key}"
        payload = {"content": {"parts": [{"text": text[:8000]}]}}
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["embedding"]["values"]
        except httpx.HTTPError:
            logger.error("Gemini embedding request failed", exc_info=True)
            raise
