"""
The retrieval swap point.

This is the single interface between the rest of the app and however
retrieval is implemented. Do not let any other file call embeddings or
a vector store directly — always go through this function, so it can
be replaced with a hosted vector DB later without touching callers
(see docs/architecture.md's scaling table).

Owned by: Voice & LLM lane.
"""


def retrieve(drug_id: str, query: str) -> list[str]:
    """
    Returns the most relevant context chunks for `query` about `drug_id`,
    ready to hand to llm/client.py::generate_answer.

    TODO: implement — filter the in-memory index (built by ingest.py) to
    chunks belonging to drug_id, embed `query` via embed.py::embed_text,
    and return the top-k chunks by similarity.
    """
    # TODO: implement
    raise NotImplementedError
