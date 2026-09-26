"""
Drug document ingestion.

Reads drug-information text files, splits them into chunks, embeds each
chunk, and builds the in-memory retrieval index.

Owned by: Voice & LLM lane (mechanics) / Content & demo lane (documents).
"""

from pathlib import Path

from .embed import embed_text
from .index import set_index


def _chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    """
    Split a document into reasonably sized chunks.

    Paragraph boundaries are preserved where possible.
    """

    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        if not current:
            current = paragraph
        elif len(current) + len(paragraph) + 2 <= max_chars:
            current += "\n\n" + paragraph
        else:
            chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def ingest_docs(folder_path: str) -> list[dict]:
    """
    Read all .txt drug documents under folder_path and build the
    in-memory retrieval index.

    The filename stem is used as the drug_id.

    Example:
        data/drug_docs/ozempic.txt
        -> drug_id = "ozempic"
    """

    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(
            f"Drug documents directory not found: {folder}"
        )

    entries = []

    # rglob allows both:
    #   drug_docs/drug.txt
    # and:
    #   drug_docs/DRUG_NAME/DRUG_ID.txt
    for file_path in folder.rglob("*.txt"):
        text = file_path.read_text(encoding="utf-8").strip()

        if not text:
            continue

        # Use the filename as the drug ID.
        drug_id = file_path.stem

        chunks = _chunk_text(text)

        for chunk in chunks:
            embedding = embed_text(chunk)

            if not embedding:
                continue

            entries.append(
                {
                    "drug_id": drug_id,
                    "text": chunk,
                    "embedding": embedding,
                }
            )

    set_index(entries)

    return entries