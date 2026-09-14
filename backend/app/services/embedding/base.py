from abc import ABC, abstractmethod


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
