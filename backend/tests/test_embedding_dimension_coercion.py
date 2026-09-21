"""Regression tests for a real production bug: switching the embedding
provider to Gemini's newer gemini-embedding-* models (which default to 3072
dimensions) crashed every CV upload with
`ValueError: expected 384 dimensions, not 3072` on the embeddings INSERT,
because the embeddings.vector column is a fixed-width pgvector column
(settings.EMBEDDING_DIM). See app/services/embedding/base.py:coerce_dimension
and its use in the Gemini/OpenAI embedding services.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.embedding.base import coerce_dimension
from app.services.embedding.gemini_service import GeminiEmbeddingService
from app.services.embedding.openai_service import OpenAIEmbeddingService


def test_coerce_dimension_passes_through_exact_match():
    values = [0.1, 0.2, 0.3]
    assert coerce_dimension(values, 3, "some-model") == values


def test_coerce_dimension_truncates_and_renormalizes_oversized_vector():
    values = [3.0, 4.0, 100.0]  # last element must be dropped by truncation
    result = coerce_dimension(values, 2, "some-model")
    assert len(result) == 2
    norm = sum(v * v for v in result) ** 0.5
    assert norm == pytest.approx(1.0)
    assert result[0] == pytest.approx(0.6)  # 3/5, from the truncated [3.0, 4.0] pair
    assert result[1] == pytest.approx(0.8)  # 4/5


def test_coerce_dimension_raises_when_vector_too_small():
    with pytest.raises(ValueError, match="fewer than the required"):
        coerce_dimension([0.1, 0.2], 4, "some-model")


def _fake_response(json_body: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = json_body
    return response


def test_gemini_embedding_service_coerces_oversized_native_output():
    oversized = [0.001] * 3072
    with patch("httpx.Client.post", return_value=_fake_response({"embedding": {"values": oversized}})):
        service = GeminiEmbeddingService(api_key="fake-key", model="gemini-embedding-2")
        vector = service.embed("Backend engineer with Python experience")
    assert len(vector) == 384
    assert service.dimensions == 384


def test_openai_embedding_service_coerces_oversized_native_output():
    oversized = [0.001] * 3072
    with patch("httpx.Client.post", return_value=_fake_response({"data": [{"embedding": oversized}]})):
        service = OpenAIEmbeddingService(api_key="fake-key", model="text-embedding-3-large")
        vector = service.embed("Backend engineer with Python experience")
    assert len(vector) == 384
    assert service.dimensions == 384
