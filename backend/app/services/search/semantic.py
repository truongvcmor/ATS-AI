import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.embedding import CandidateEmbedding
from app.services.embedding.base import EmbeddingService


class SemanticSearch:
    """Cosine-similarity search over the `embeddings` table (pgvector).

    Swappable for Qdrant/OpenSearch/Elasticsearch later: callers only ever
    see {candidate_id: similarity} — nothing here leaks into the API layer.
    """

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    def search(
        self, db: Session, query_text: str, candidate_ids: list[uuid.UUID] | None = None
    ) -> dict[uuid.UUID, float]:
        query_vector = self._embedding_service.embed(query_text)
        stmt = select(
            CandidateEmbedding.candidate_id,
            CandidateEmbedding.vector.cosine_distance(query_vector).label("distance"),
        )
        if candidate_ids is not None:
            if not candidate_ids:
                return {}
            stmt = stmt.where(CandidateEmbedding.candidate_id.in_(candidate_ids))
        rows = db.execute(stmt).all()
        # cosine_distance is 0 (identical) .. 2 (opposite); convert to a 0..1 similarity score.
        return {row.candidate_id: max(0.0, 1.0 - (row.distance / 2.0)) for row in rows}
