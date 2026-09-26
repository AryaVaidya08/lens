"""
Text embedding helper.

Loads the embedding model once and exposes a single function for
converting text into an embedding vector.

Owned by: Voice & LLM lane.
"""

from sentence_transformers import SentenceTransformer


# Loaded once when the backend starts.
# The first run may download the model.
_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    """
    Convert text into an embedding vector.

    Returns an empty list for empty input.
    """

    if not isinstance(text, str) or not text.strip():
        return []

    embedding = _model.encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()