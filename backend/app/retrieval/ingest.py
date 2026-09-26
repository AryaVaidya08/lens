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
import re
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
    normalized = text.replace("\r\n", "\n")
    parts = [block.strip() for block in normalized.split("\n\n")]
    parts = [part for part in parts if part]
    if len(parts) <= 1 and "\n" in normalized:
        # Some sources (raw label field dumps: "field_name:\n  value") have
        # no blank-line paragraph breaks at all, which otherwise collapses
        # the whole doc into a single oversized chunk. Fall back to
        # single-newline splitting so each field still gets its own chunk.
        parts = [line.strip() for line in normalized.split("\n") if line.strip()]
    return parts


def _split_oversized(paragraph: str) -> list[str]:
    """Hard-splits a single paragraph that's far bigger than the target
    (e.g. one huge table or field value with no internal breaks) into
    fixed-size windows, so it doesn't become one giant, mostly-truncated
    embedding and an oversized context blob handed to the LLM."""
    limit = TARGET_CHUNK_CHARS * 2
    if len(paragraph) <= limit:
        return [paragraph]
    windows = [paragraph[i : i + TARGET_CHUNK_CHARS].strip() for i in range(0, len(paragraph), TARGET_CHUNK_CHARS)]
    return [window for window in windows if window]


def chunk_text(text: str) -> list[str]:
    """Paragraph chunks, merged up to TARGET_CHUNK_CHARS."""
    paragraphs = _split_paragraphs(text)
    paragraphs = [piece for para in paragraphs for piece in _split_oversized(para)]
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


_FIELD_HEADER = re.compile(r"^[a-z0-9_]+:$")
_SECTION_HEADER = re.compile(r"^##\s+(.+)$")


def _slugify_field_name(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.strip().lower()).strip("_")


def _parse_raw_field_dump(text: str) -> dict[str, str]:
    """Corpus format: an unindented "field_name:" line followed by one or
    more indented lines holding that field's text (no blank-line breaks)."""
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_value: list[str] = []
    for line in text.splitlines():
        if not line.startswith((" ", "\t")) and _FIELD_HEADER.match(line.strip()):
            if current_key is not None:
                fields[current_key] = " ".join(current_value).strip()
            current_key = line.strip().rstrip(":")
            current_value = []
        elif current_key is not None and line.strip():
            current_value.append(line.strip())
    if current_key is not None:
        fields[current_key] = " ".join(current_value).strip()
    return fields


def _parse_section_headers(text: str) -> dict[str, str]:
    """Older corpus format (scripts/curate_openfda.py's output): a
    "## Section Title" line followed by that section's text, blank-line
    separated. Title is slugified to match the raw-dump format's keys
    (e.g. "## Indications and usage" -> "indications_and_usage")."""
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_value: list[str] = []
    for line in text.splitlines():
        match = _SECTION_HEADER.match(line.strip())
        if match:
            if current_key is not None:
                fields[current_key] = " ".join(current_value).strip()
            current_key = _slugify_field_name(match.group(1))
            current_value = []
        elif current_key is not None and line.strip():
            current_value.append(line.strip())
    if current_key is not None:
        fields[current_key] = " ".join(current_value).strip()
    return fields


def parse_dossier_fields(drug_id: str, folder_path: str | None = None) -> dict[str, str]:
    """
    Reads the raw drug_docs file for `drug_id` and returns {field_name: value}.

    The corpus mixes two formats: most docs are a raw label field dump
    (see _parse_raw_field_dump), but some (from an earlier version of
    scripts/curate_openfda.py) use "## Section Title" headers instead (see
    _parse_section_headers). Returns {} if the file can't be found. Used by
    personalization/scorer.py to pick which fields to surface for the HUD
    summary — separate from chunk_text above, which is for embeddings, not
    named-field lookup.
    """
    root = Path(folder_path or settings.drug_docs_path)
    for drug_id_found, path in _iter_doc_files(root):
        if drug_id_found != drug_id:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^##\s+\S", text):
            return _parse_section_headers(text)
        return _parse_raw_field_dump(text)
    return {}
