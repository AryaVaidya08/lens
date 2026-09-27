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

from app.config import settings
from app.retrieval.embed import embed_text
from app.retrieval.types import Chunk
from app.text import content_terms


# A question that names a section ("what are the side effects") should land
# on that section even when another section happens to repeat the same word
# more often.
_SECTION_MATCH_BONUS = 0.2
_SPECIALTY_SECTION_BONUS = 0.05

# Temporary compatibility with the existing llm-rag ingest.py.
# Once ingest.py is resolved, it should call load() directly.
_chunks: list[Chunk] = []


def load(chunks: list[Chunk]) -> None:
    """Install the index built by ingest.py."""
    global _chunks
    _chunks = list(chunks)


def append_chunks(chunks: list[Chunk]) -> None:
    """Add one dossier's chunks without dropping the rest of the index."""
    global _chunks
    if chunks:
        _chunks.extend(chunks)


def set_index(chunks: list[Chunk]) -> None:
    """
    Backward-compatible alias for the old ingest.py interface.

    This can be removed later once ingest.py is updated to call load().
    """
    load(chunks)


def get_index() -> list[Chunk]:
    """Return the currently loaded in-memory index."""
    return _chunks


def chunk_count() -> int:
    """Return the number of chunks currently loaded into the index."""
    return len(_chunks)


def _cosine(a: list[float], b: list[float]) -> float:
    """
    Compute cosine similarity.

    Embeddings produced by embed.py are normalized, so their dot product
    is equivalent to cosine similarity.
    """
    return sum(x * y for x, y in zip(a, b))


# Allergy / medication questions need the contraindication passage even when
# another section happens to embed closer to the wording of the question.
_SAFETY_QUERY_MARKERS = (
    "allerg",
    "medicat",
    "interact",
    "conflict",
    "contraindic",
    "hypersensit",
)


def _candidates_for(drug_id: str) -> list[Chunk]:
    exact = [chunk for chunk in _chunks if chunk.drug_id == drug_id]
    if exact:
        return exact
    needle = drug_id.strip().lower()
    if not needle:
        return []
    return [chunk for chunk in _chunks if chunk.drug_id.lower() == needle]


def _query_asks_about_chart_safety(query_terms: set[str]) -> bool:
    blob = " ".join(query_terms)
    return any(marker in blob for marker in _SAFETY_QUERY_MARKERS)


def _safety_priority(chunk: Chunk) -> int | None:
    """Lower is more relevant. None means the passage is not a safety pin."""
    section = (chunk.section or "").lower().replace("_", " ")
    text = chunk.text.lower()
    short = len(chunk.text) < 2500
    if "contraindic" in section or (
        short and ("hypersensitive" in text or "contraindicat" in text)
    ):
        return 0
    if short and "sensitive skin" in text:
        return 0
    if any(hint in section for hint in ("warning", "boxed", "ask doctor")):
        return 1 if short else 6
    if any(hint in section for hint in ("adverse", "allerg", "when using", "stop use")):
        return 2 if short else 7
    if any(hint in section for hint in ("precaution", "interaction", "ingredient")):
        return 3 if short else 8
    return None


def _with_safety_passages(
    ranked: list[Chunk],
    candidates: list[Chunk],
    limit: int,
) -> list[Chunk]:
    pinned = [chunk for chunk in candidates if _safety_priority(chunk) is not None]
    pinned.sort(key=lambda chunk: (_safety_priority(chunk) or 0, len(chunk.text)))
    chosen: list[Chunk] = []
    seen: set[str] = set()
    for chunk in pinned[:2] + ranked:
        if chunk.text in seen:
            continue
        seen.add(chunk.text)
        chosen.append(chunk)
        if len(chosen) >= limit:
            break
    return chosen


def retrieve(
    drug_id: str,
    query: str,
    top_k: int | None = None,
    specialty: str | None = None,
) -> list[str]:
    """
    Return the most relevant context chunks for `query` about `drug_id`.

    Filters by drug_id first so a question about one drug can never pull
    context from another drug's dossier. Results are then ranked using
    embedding similarity with an additional bonus when the query terms
    explicitly match the chunk's section name.

    If startup ingest was skipped and this drug is not in the index yet,
    its dossier file is loaded on demand. Callers still go through this
    function; nothing else should touch the index.
    """

    candidates = _candidates_for(drug_id)
    if not candidates:
        from app.retrieval.ingest import ensure_drug_indexed

        if ensure_drug_indexed(drug_id):
            candidates = _candidates_for(drug_id)

    if not candidates:
        return []

    limit = top_k or settings.retrieval_top_k

    query_vector = embed_text(query)
    query_terms = set(content_terms(query))
    from app.personalization.scorer import specialty_section_keys

    specialty_terms: set[str] = set()
    for key in specialty_section_keys(specialty):
        specialty_terms |= set(content_terms(key.replace("_", " ")))

    def score(chunk: Chunk) -> float:
        semantic_score = _cosine(
            query_vector,
            chunk.embedding,
        )

        section_terms = set(content_terms(chunk.section))
        section_overlap = query_terms & section_terms
        specialty_overlap = section_terms & specialty_terms

        return (
            semantic_score
            + _SECTION_MATCH_BONUS * len(section_overlap)
            + _SPECIALTY_SECTION_BONUS * len(specialty_overlap)
        )

    ranked = sorted(
        candidates,
        key=score,
        reverse=True,
    )
    chosen = ranked[:limit]
    if _query_asks_about_chart_safety(query_terms):
        chosen = _with_safety_passages(ranked, candidates, limit)

    return [chunk.text for chunk in chosen]