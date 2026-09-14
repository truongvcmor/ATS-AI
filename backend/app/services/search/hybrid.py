import uuid


class HybridSearch:
    """Combines keyword-match and semantic-similarity scores into one relevance score."""

    def __init__(self, keyword_weight: float = 0.5, semantic_weight: float = 0.5) -> None:
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight

    def combine(
        self,
        keyword_scores: dict[uuid.UUID, float],
        semantic_scores: dict[uuid.UUID, float],
    ) -> dict[uuid.UUID, float]:
        ids = set(keyword_scores) | set(semantic_scores)
        return {
            cid: keyword_scores.get(cid, 0.0) * self.keyword_weight + semantic_scores.get(cid, 0.0) * self.semantic_weight
            for cid in ids
        }
