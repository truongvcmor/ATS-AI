import logging

import httpx

from app.core.config import settings
from app.services.embedding.base import EmbeddingService, coerce_dimension

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        # The embeddings.vector column is a fixed-width pgvector column
        # (settings.EMBEDDING_DIM) shared across providers. embed() always
        # returns a vector of exactly this width — see the truncation logic
        # below — so this is the true, guaranteed dimension regardless of
        # which Gemini embedding model is configured.
        return settings.EMBEDDING_DIM

    def embed(self, text: str) -> list[float]:
        url = f"{GEMINI_API_BASE}/{self._model}:embedContent?key={self._api_key}"
        target_dim = settings.EMBEDDING_DIM
        payload = {
            "content": {"parts": [{"text": text[:8000]}]},
            # Gemini's gemini-embedding-* models are trained with Matryoshka
            # representation learning and support requesting a smaller
            # output directly; older models (e.g. text-embedding-004) ignore
            # unknown fields, so this is safe to send unconditionally.
            "outputDimensionality": target_dim,
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                values = data["embedding"]["values"]
        except httpx.HTTPError:
            logger.error("Gemini embedding request failed", exc_info=True)
            raise

        return coerce_dimension(values, target_dim, self._model)
