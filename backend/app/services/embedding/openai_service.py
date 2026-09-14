import logging

import httpx

from app.services.embedding.base import EmbeddingService

logger = logging.getLogger(__name__)

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"

_MODEL_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return _MODEL_DIMENSIONS.get(self._model, 1536)

    def embed(self, text: str) -> list[float]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {"model": self._model, "input": text[:8000]}
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(OPENAI_EMBEDDINGS_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except httpx.HTTPError:
            logger.error("OpenAI embedding request failed", exc_info=True)
            raise
