"""
Text embedding helper.

Owned by: Voice & LLM lane. Called only from ingest.py (build time) and
index.py (query time) — no other file should import this directly.
"""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache

from app.config import settings
from app.text import content_terms


# Wide enough that a query term rarely collides with an unrelated term in a
# chunk. Used only when sentence-transformers is unavailable.
_FALLBACK_DIMENSIONS = 8192

_model = None
_model_loaded = False


@lru_cache(maxsize=1)
def _load_model():
    """
    Loads sentence-transformers once, if available.

    The hackathon demo should still be able to run without the model installed,
    so failures fall back to lexical embeddings instead of crashing startup.
    """
    global _model, _model_loaded

    if _model_loaded:
        return _model

    _model_loaded = True

    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.embedding_model)
    except Exception:
        _model = None

    return _model


def _lexical_embedding(text: str) -> list[float]:
    """
    Hashed bag-of-content-words, L2 normalized.

    This is a fallback for environments where sentence-transformers or its
    model weights are unavailable.
    """
    counts: dict[int, int] = {}

    for token in content_terms(text):
        digest = hashlib.blake2b(
            token.encode("utf-8"),
            digest_size=4,
        ).digest()
        bucket = int.from_bytes(digest, "big") % _FALLBACK_DIMENSIONS
        counts[bucket] = counts.get(bucket, 0) + 1

    # Sublinear term frequency: repeated mentions of one word should not
    # overwhelm the rest of the query.
    vector = [0.0] * _FALLBACK_DIMENSIONS

    for bucket, count in counts.items():
        vector[bucket] = 1.0 + math.log(count)

    norm = math.sqrt(sum(value * value for value in vector))

    if norm == 0:
        return vector

    return [value / norm for value in vector]


def embed_text(text: str) -> list[float]:
    """Return a normalized embedding vector for one piece of text."""
    if not isinstance(text, str) or not text.strip():
        return []

    model = _load_model()

    if model is None:
        return _lexical_embedding(text)

    vector = model.encode(
        text,
        normalize_embeddings=True,
    )

    return [float(value) for value in vector]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batch encode texts.

    Used by ingest.py so the sentence-transformers model can process the
    document corpus efficiently rather than encoding one chunk at a time.
    """
    if not texts:
        return []

    model = _load_model()

    if model is None:
        return [_lexical_embedding(text) for text in texts]

    matrix = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=False,
    )

    return [row.tolist() for row in matrix]


def using_model() -> bool:
    """Return True when real sentence-transformers embeddings are available."""
    return _load_model() is not None