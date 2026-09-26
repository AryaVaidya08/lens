"""
The retrieval swap point.

This is the single interface between the rest of the app and however
retrieval is implemented. Do not let any other file call embeddings or
a vector store directly — always go through this function, so it can
be replaced with a hosted vector DB later without touching callers
(see docs/architecture.md's scaling table).

Owned by: Voice & LLM lane.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.retrieval.embed import embed_text

_TOP_K = 6


@dataclass
class Chunk:
    drug_id: str
    text: str
    embedding: list[float]


_INDEX: list[Chunk] = []


def set_index(chunks: list[Chunk]) -> None:
    """Replace the in-memory index. Called by ingest_docs at startup."""
    global _INDEX
    _INDEX = list(chunks)


def get_index() -> list[Chunk]:
    return _INDEX


def retrieve(drug_id: str, query: str) -> list[str]:
    """
    Returns the most relevant context chunks for `query` about `drug_id`,
    ready to hand to llm/client.py::generate_answer.

    Filters to this drug first, then ranks by cosine similarity.
    """
    pool = [chunk for chunk in _INDEX if chunk.drug_id == drug_id]
    if not pool:
        # Filename stems are the canonical id; also accept folder-style slugs.
        needle = drug_id.strip().lower()
        pool = [chunk for chunk in _INDEX if chunk.drug_id.lower() == needle]
    if not pool:
        return []

    query_vec = np.array(embed_text(query), dtype=np.float32)
    scored: list[tuple[float, str]] = []
    for chunk in pool:
        vec = np.array(chunk.embedding, dtype=np.float32)
        score = float(np.dot(query_vec, vec))
        scored.append((score, chunk.text))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [text for _, text in scored[:_TOP_K]]
