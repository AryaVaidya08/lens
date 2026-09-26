"""
Text embedding helper.

Owned by: Voice & LLM lane. Called only from ingest.py (build time) and
index.py (query time) — no other file should import this directly.
"""


def embed_text(text: str) -> list[float]:
    """
    Returns an embedding vector for `text`.

    TODO: implement — wrap a sentence-transformers model
    (e.g. all-MiniLM-L6-v2) loaded once at module import time.
    """
    # TODO: implement
    raise NotImplementedError
