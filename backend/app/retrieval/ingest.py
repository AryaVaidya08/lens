"""
Drug doc ingestion.

Reads all files in backend/data/drug_docs/, chunks and embeds them, and
builds the in-memory index used by index.py::retrieve. Runs once at
backend startup.

Owned by: Voice & LLM lane (mechanics) / Content & demo lane (the docs
themselves, see backend/data/drug_docs/).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from app.config import settings
from app.retrieval.embed import embed_texts
from app.retrieval.index import Chunk, set_index

TARGET_CHUNK_CHARS = 900
MIN_CHUNK_CHARS = 120


def _iter_doc_files(folder_path: Path) -> list[tuple[str, Path]]:
    """
    Yields (drug_id, path) for every dossier.

    Expected layout: <DRUG_NAME>/<DRUG_ID>.txt
    Loose .txt files directly under drug_docs/ are also accepted
    (drug_id = filename stem).
    """
    found: list[tuple[str, Path]] = []
    if not folder_path.exists():
        return found

    for child in sorted(folder_path.iterdir()):
        if child.name.startswith(".") or child.name == "manifest.json":
            continue
        if child.is_dir():
            for txt in sorted(child.glob("*.txt")):
                found.append((txt.stem, txt))
        elif child.suffix.lower() == ".txt":
            found.append((child.stem, child))
    return found


def _split_paragraphs(text: str) -> list[str]:
    parts = [block.strip() for block in text.replace("\r\n", "\n").split("\n\n")]
    return [part for part in parts if part]


def chunk_text(text: str) -> list[str]:
    """Paragraph chunks, merged up to TARGET_CHUNK_CHARS."""
    paragraphs = _split_paragraphs(text)
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + 2 + len(para) > TARGET_CHUNK_CHARS:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}".strip() if current else para
    if current:
        chunks.append(current)

    merged: list[str] = []
    for chunk in chunks:
        if merged and len(chunk) < MIN_CHUNK_CHARS:
            merged[-1] = f"{merged[-1]}\n\n{chunk}"
        else:
            merged.append(chunk)
    return merged or [text.strip()]


def _cache_key(drug_id: str, path: Path, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{drug_id}:{path.name}:{digest}"


def _keys_path(cache_path: Path) -> Path:
    return cache_path.with_suffix(".keys.json")


def _load_cache(cache_path: Path) -> dict[str, list[float]]:
    keys_path = _keys_path(cache_path)
    if not cache_path.exists() or not keys_path.exists():
        return {}
    try:
        keys = json.loads(keys_path.read_text(encoding="utf-8"))
        payload = np.load(cache_path)
        vectors = payload["vectors"]
        if len(keys) != len(vectors):
            return {}
        return {key: vectors[i].tolist() for i, key in enumerate(keys)}
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return {}


def _save_cache(cache_path: Path, cache: dict[str, list[float]]) -> None:
    if not cache:
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(cache.keys())
    vectors = np.array([cache[key] for key in keys], dtype=np.float32)
    np.savez_compressed(cache_path, vectors=vectors)
    _keys_path(cache_path).write_text(json.dumps(keys), encoding="utf-8")


def ingest_docs(folder_path: str | None = None) -> list[Chunk]:
    """
    Builds and returns the in-memory retrieval index from every file in
    `folder_path`.
    """
    root = Path(folder_path or settings.drug_docs_path)
    cache_path = Path(settings.embedding_cache_path)
    cache = _load_cache(cache_path)

    pending_texts: list[str] = []
    pending_meta: list[tuple[str, str]] = []  # drug_id, cache_key
    ready: list[Chunk] = []

    for drug_id, path in _iter_doc_files(root):
        raw = path.read_text(encoding="utf-8")
        for chunk in chunk_text(raw):
            key = _cache_key(drug_id, path, chunk)
            if key in cache:
                ready.append(Chunk(drug_id=drug_id, text=chunk, embedding=cache[key]))
            else:
                pending_texts.append(chunk)
                pending_meta.append((drug_id, key))

    if pending_texts:
        vectors = embed_texts(pending_texts)
        for (drug_id, key), text, vector in zip(pending_meta, pending_texts, vectors):
            cache[key] = vector
            ready.append(Chunk(drug_id=drug_id, text=text, embedding=vector))
        _save_cache(cache_path, cache)

    set_index(ready)
    return ready
