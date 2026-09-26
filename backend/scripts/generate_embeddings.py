"""
Pre-builds the RAG embedding cache for every drug doc in backend/data/drug_docs/.

This doesn't reimplement retrieval — it just calls the same
ingest_docs() the FastAPI app runs at startup (see
app/retrieval/ingest.py), so the app boots instantly against a warm
cache instead of re-embedding ~1700 dossiers on every `uvicorn --reload`.

Usage (from backend/):
  python scripts/generate_embeddings.py
  python scripts/generate_embeddings.py --docs-path data/drug_docs
  python scripts/generate_embeddings.py --rebuild   # ignore existing cache
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and cache drug doc embeddings for RAG.")
    parser.add_argument("--docs-path", default=settings.drug_docs_path, help="Folder of drug dossiers to ingest.")
    parser.add_argument("--cache-path", default=settings.embedding_cache_path, help="Where to save the embedding cache.")
    parser.add_argument("--rebuild", action="store_true", help="Delete any existing cache first and re-embed everything.")
    args = parser.parse_args()

    settings.drug_docs_path = args.docs_path
    settings.embedding_cache_path = args.cache_path

    if args.rebuild:
        cache_path = Path(args.cache_path)
        keys_path = cache_path.with_suffix(".keys.json")
        for path in (cache_path, keys_path):
            if path.exists():
                path.unlink()

    from app.retrieval.ingest import ingest_docs

    docs_root = Path(args.docs_path)
    if not docs_root.exists():
        print(f"error: docs path does not exist: {docs_root}", file=sys.stderr)
        return 1

    print(f"Embedding model: {settings.embedding_model}")
    print(f"Docs path:       {docs_root}")
    print(f"Cache path:      {args.cache_path}")
    print("Ingesting + embedding drug docs (this warms the cache; cached chunks are skipped)...")

    started = time.time()
    chunks = ingest_docs(str(docs_root))
    elapsed = time.time() - started

    drug_ids = {chunk.drug_id for chunk in chunks}
    print(
        f"Done in {elapsed:.1f}s — {len(drug_ids)} drugs, {len(chunks)} chunks, "
        f"{len(chunks) / elapsed:.1f} chunks/sec." if elapsed > 0 else "Done (all cached)."
    )
    print(f"Cache saved to: {args.cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
