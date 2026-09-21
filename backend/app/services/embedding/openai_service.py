import logging

import httpx

from app.core.config import settings
from app.services.embedding.base import EmbeddingService, coerce_dimension

logger = logging.getLogger(__name__)

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"

# text-embedding-ada-002 doesn't support the `dimensions` request param —
# everything else does (and ignoring an unsupported dimensions value for a
# model that doesn't accept it would be an API error, so we only send it
# for models known to support truncation).
_SUPPORTS_DIMENSIONS_PARAM = {"text-embedding-3-small", "text-embedding-3-large"}


class OpenAIEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        # See GeminiEmbeddingService.dimensions — embed() always coerces to
        # this fixed width, so it's the true guaranteed dimension.
        return settings.EMBEDDING_DIM

    def embed(self, text: str) -> list[float]:
        target_dim = settings.EMBEDDING_DIM
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {"model": self._model, "input": text[:8000]}
        if self._model in _SUPPORTS_DIMENSIONS_PARAM:
            payload["dimensions"] = target_dim
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(OPENAI_EMBEDDINGS_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                values = data["data"][0]["embedding"]
        except httpx.HTTPError:
            logger.error("OpenAI embedding request failed", exc_info=True)
            raise

        return coerce_dimension(values, target_dim, self._model)
