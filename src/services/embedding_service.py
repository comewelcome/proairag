import math
from src.config import get_settings

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class EmbeddingService:
    def __init__(self):
        settings = get_settings()
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self.model = SentenceTransformer(settings.embedding_model)
        else:
            self.model = None
        self.dimension = settings.embedding_dimension

    async def embed_text(self, text: str) -> list[float]:
        if self.model is None:
            return self._fallback_embed(text)
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.model is None:
            return [self._fallback_embed(t) for t in texts]
        embeddings = self.model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return embeddings.tolist()

    async def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _fallback_embed(text: str, dim: int = 384) -> list[float]:
        """Fallback hash-based embedding when sentence-transformers is not installed."""
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        values = [int(b) / 255.0 for b in hash_bytes * (dim // 32 + 1)]
        # Normalize
        norm = math.sqrt(sum(v * v for v in values[:dim])) or 1.0
        return [v / norm for v in values[:dim]]


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
