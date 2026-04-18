import logging
import os
from typing import List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class EmbeddingService:
    """Generates and manages text embeddings for RAG pipeline."""

    def __init__(self):
        self.client = None
        self.model = getattr(settings, "EMBEDDING_MODEL", "text-embedding-3-small")
        self.dimension = getattr(settings, "EMBEDDING_DIMENSION", 1536)
        if HAS_OPENAI and getattr(settings, "OPENAI_API_KEY", ""):
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def is_available(self) -> bool:
        return self.client is not None

    def generate(self, text: str) -> Optional[List[float]]:
        if not self.client or not text.strip():
            return None
        try:
            response = self.client.embeddings.create(
                input=text[:8000],
                model=self.model,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            return None

    def generate_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        if not self.client:
            return [None] * len(texts)
        results = []
        for text in texts:
            results.append(self.generate(text))
        return results

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
