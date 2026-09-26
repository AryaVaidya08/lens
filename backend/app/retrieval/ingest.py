"""
Drug doc ingestion.

Reads all files in backend/data/drug_docs/, chunks and embeds them, and
builds the in-memory index used by index.py::retrieve. Runs once at
backend startup.

Owned by: Voice & LLM lane (mechanics) / Content & demo lane (the docs
themselves, see backend/data/drug_docs/).
"""


def ingest_docs(folder_path: str):
    """
    Builds and returns the in-memory retrieval index from every file in
    `folder_path`.

    TODO: implement — read each file, chunk it (e.g. by paragraph or
    fixed token window), call embed.py::embed_text per chunk, and store
    (drug_id, chunk_text, embedding) tuples for index.py to filter over.
    """
    # TODO: implement
    raise NotImplementedError
