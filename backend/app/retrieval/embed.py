"""
Text embedding helper.

Owned by: Voice & LLM lane. Called only from ingest.py (build time) and
index.py (query time) — no other file should import this directly.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def embed_text(text: str) -> list[float]:
    """
    Returns an embedding vector for `text`.

    Wraps a sentence-transformers model loaded once at first use.
    """
    vector = _model().encode(text or "", normalize_embeddings=True)
    return vector.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch encode — used by ingest so we don't load the model per chunk."""
    if not texts:
        return []
    matrix = _model().encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    return [row.tolist() for row in matrix]
