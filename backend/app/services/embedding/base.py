import logging
import math
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


def coerce_dimension(values: list[float], target_dim: int, model: str) -> list[float]:
    """Guarantee a vector fits the fixed-width pgvector column regardless of
    whether a provider's API honored a requested output size — some models
    ignore it and return their native size, which would otherwise crash the
    embeddings INSERT with a Postgres dimension mismatch."""
    if len(values) == target_dim:
        return values
    if len(values) < target_dim:
        raise ValueError(
            f"Embedding model '{model}' returned {len(values)} dimensions, fewer than the "
            f"required {target_dim}. Pick a different embedding model in Settings."
        )
    # Matryoshka-trained embeddings keep their most important signal in the
    # leading dimensions, so a prefix truncation is meaningful — but the
    # truncated vector is no longer guaranteed unit-norm, so renormalize.
    truncated = values[:target_dim]
    norm = math.sqrt(sum(v * v for v in truncated))
    if norm > 0:
        truncated = [v / norm for v in truncated]
    logger.warning(
        "Embedding model '%s' returned %s dimensions; truncated to %s to match the pgvector column.",
        model,
        len(values),
        target_dim,
    )
    return truncated


class EmbeddingService(ABC):
    """Provider-agnostic text -> vector abstraction, so the vector backend
    (pgvector today, Qdrant/OpenSearch/Elasticsearch later) never has to
    know which model produced the numbers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimensions(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError
