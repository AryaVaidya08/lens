"""
The retrieval swap point.

This is the single interface between the rest of the app and however
retrieval is implemented. Do not let any other file call embeddings or
a vector store directly — always go through this function, so it can
be replaced with a hosted vector DB later without touching callers
(see docs/architecture.md's scaling table).

Owned by: Voice & LLM lane.
"""

from typing import Optional

from app.config import settings
from app.retrieval.embed import embed_text
from app.retrieval.ingest import Chunk
from app.text import content_terms

# A question that names a section ("what are the side effects") should land on
# that section even when another section happens to repeat the same word more
# often — "dose related" appears all over Side effects, but a dosing question
# belongs to Dosing.
_SECTION_MATCH_BONUS = 0.2

_chunks: list[Chunk] = []


def load(chunks: list[Chunk]) -> None:
    """Installs the index built by ingest.py. Called once at startup."""
    global _chunks
    _chunks = chunks


def chunk_count() -> int:
    """Surfaced by /health so a broken ingest is visible without reading logs."""
    return len(_chunks)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def retrieve(drug_id: str, query: str, top_k: Optional[int] = None) -> list[str]:
    """
    Returns the most relevant context chunks for `query` about `drug_id`,
    ready to hand to llm/client.py::generate_answer.

    Filters by drug_id *first* so a question about one drug can never pull in
    another drug's dossier, then ranks within that drug by cosine similarity.
    """
    candidates = [chunk for chunk in _chunks if chunk.drug_id == drug_id]
    if not candidates:
        return []

    limit = top_k or settings.retrieval_top_k
    query_vector = embed_text(query)
    query_terms = set(content_terms(query))

    def score(chunk: Chunk) -> float:
        overlap = query_terms & set(content_terms(chunk.section))
        return _cosine(query_vector, chunk.embedding) + _SECTION_MATCH_BONUS * len(overlap)

    ranked = sorted(candidates, key=score, reverse=True)
    return [chunk.text for chunk in ranked[:limit]]
