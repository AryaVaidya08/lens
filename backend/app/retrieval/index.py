"""
The retrieval swap point.

This is the single interface between the rest of the app and however
retrieval is implemented. Do not let any other file call embeddings or
a vector store directly — always go through this function.

Owned by: Voice & LLM lane.
"""

import numpy as np

from .embed import embed_text


# Each entry is:
# {
#     "drug_id": str,
#     "text": str,
#     "embedding": list[float],
# }
_index: list[dict] = []


def set_index(entries: list[dict]) -> None:
    """
    Replace the current in-memory retrieval index.

    Called by ingest.py after drug documents have been processed.
    """
    global _index
    _index = entries


def retrieve(drug_id: str, query: str) -> list[str]:
    """
    Returns the most relevant context chunks for `query` about `drug_id`.

    Only chunks belonging to the requested drug are considered.
    Results are ranked using cosine similarity.
    """

    if not query.strip():
        return []

    # Only search chunks belonging to this drug.
    candidates = [
        entry
        for entry in _index
        if entry["drug_id"] == drug_id
    ]

    if not candidates:
        return []

    query_embedding = np.array(embed_text(query), dtype=float)

    query_norm = np.linalg.norm(query_embedding)

    if query_norm == 0:
        return []

    scored = []

    for entry in candidates:
        embedding = np.array(entry["embedding"], dtype=float)
        embedding_norm = np.linalg.norm(embedding)

        if embedding_norm == 0:
            continue

        similarity = np.dot(query_embedding, embedding) / (
            query_norm * embedding_norm
        )

        scored.append((similarity, entry["text"]))

    scored.sort(reverse=True, key=lambda item: item[0])

    # Return the top 5 chunks.
    return [text for _, text in scored[:5]]