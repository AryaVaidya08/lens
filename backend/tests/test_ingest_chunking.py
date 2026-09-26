from app.retrieval.ingest import chunk_text


def test_chunk_text_keeps_sections():
    text = "## Indications\nTreats type 2 diabetes.\n\n## Dosage\nStart at 0.25 mg once weekly."
    chunks = chunk_text(text)
    assert chunks
    joined = "\n".join(chunks)
    assert "diabetes" in joined
    assert "0.25 mg" in joined
