"""
Text embedding helper.

Owned by: Voice & LLM lane. Called only from ingest.py (build time) and
index.py (query time) — no other file should import this directly.
"""

import hashlib
import math

from app.text import content_terms

# Wide enough that a query term rarely collides with an unrelated term in a
# chunk. At 512 it collided often enough to rank the wrong section first.
_FALLBACK_DIMENSIONS = 8192
_model = None
_model_loaded = False


def _load_model():
    """
    Loads sentence-transformers once, if it is installed and its weights are
    already available. A hackathon demo laptop may be offline or may not have
    the (large) dependency installed, so this must never be fatal — the lexical
    fallback below keeps retrieval working either way.
    """
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _model = None
    return _model


def _lexical_embedding(text: str) -> list[float]:
    """
    Hashed bag-of-content-words, L2 normalized, so cosine similarity ranks by
    meaningful term overlap. Stopwords are dropped because without that, every
    chunk matches every question on "the" and "is" and ranking becomes noise.
    """
    counts: dict = {}
    for token in content_terms(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
        bucket = int.from_bytes(digest, "big") % _FALLBACK_DIMENSIONS
        counts[bucket] = counts.get(bucket, 0) + 1

    # Sublinear term frequency: a section that says "dose" six times in passing
    # shouldn't outrank the section that is actually about dosing.
    vector = [0.0] * _FALLBACK_DIMENSIONS
    for bucket, count in counts.items():
        vector[bucket] = 1.0 + math.log(count)

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def embed_text(text: str) -> list[float]:
    """Returns an embedding vector for `text`."""
    model = _load_model()
    if model is None:
        return _lexical_embedding(text)
    return [float(value) for value in model.encode(text, normalize_embeddings=True)]


def using_model() -> bool:
    """True when real sentence-transformers embeddings are in use. Surfaced by /health."""
    return _load_model() is not None
