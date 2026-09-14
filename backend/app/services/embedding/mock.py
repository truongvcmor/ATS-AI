import hashlib
import math
import re

from app.services.embedding.base import EmbeddingService

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.]*")


def _stable_hash(token: str) -> int:
    # Python's built-in hash() is randomized per-process for strings, which
    # would make this "deterministic" embedding drift across restarts. Use a
    # stable digest instead so the same text always maps to the same vector.
    return int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)


class MockEmbeddingService(EmbeddingService):
    """Deterministic local embedding using the hashing trick (feature hashing).

    No external API or ML runtime required, so semantic search still works
    with zero API keys and zero heavy dependencies. Documents that share
    vocabulary land closer together in cosine-similarity space, which is
    enough to demonstrate real semantic search behavior in the MVP.
    Swap for OpenAIEmbeddingService (or a local sentence-transformers model)
    without touching any caller — they all just call `.embed(text)`.
    """

    def __init__(self, dimensions: int = 384) -> None:
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return f"hashing-{self._dimensions}d"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        tokens = TOKEN_RE.findall(text.lower())
        for i, token in enumerate(tokens):
            # 2-gram context (adjacent tokens) so word order/co-occurrence matters a little.
            grams = [token] if i == 0 else [token, f"{tokens[i-1]}_{token}"]
            for gram in grams:
                h = _stable_hash(gram)
                bucket = h % self._dimensions
                sign = 1.0 if (h >> 1) % 2 == 0 else -1.0
                vector[bucket] += sign

        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]
