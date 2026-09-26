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
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.config import settings
from app.retrieval.embed import embed_texts
from app.retrieval.index import load
from app.retrieval.types import Chunk

TARGET_CHUNK_CHARS = 900
MIN_CHUNK_CHARS = 120

@dataclass
class Dossier:
    """Parsed representation of one drug document."""

    drug_id: str
    name: str
    barcode: str = ""
    headline: str = ""
    aliases: list[str] = field(default_factory=list)
    sections: dict[str, dict] = field(default_factory=dict)

    def bullets(self, section: str) -> list[str]:
        return self.sections.get(section, {}).get("bullets", [])

    def prose(self, section: str) -> str:
        return self.sections.get(section, {}).get("prose", "")


def _iter_doc_files(folder_path: Path) -> list[tuple[str, Path]]:
    """
    Yield (drug_id, path) for every dossier.

    Supports both:

        drug_docs/<drug_id>.txt

    and:

        drug_docs/<drug_name>/<drug_id>.txt
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

    parts = [
        block.strip()
        for block in normalized.split("\n\n")
        if block.strip()
    ]

    if len(parts) <= 1 and "\n" in normalized:
        # Raw label dumps often use:
        #
        # field_name:
        #   value
        #
        # with no blank lines. Split those into smaller pieces rather than
        # embedding the entire document as one huge chunk.
        parts = [
            line.strip()
            for line in normalized.split("\n")
            if line.strip()
        ]

    return parts


def _split_oversized(paragraph: str) -> list[str]:
    """
    Hard-split paragraphs that are much larger than the target size.
    """
    limit = TARGET_CHUNK_CHARS * 2

    if len(paragraph) <= limit:
        return [paragraph]

    windows = [
        paragraph[i : i + TARGET_CHUNK_CHARS].strip()
        for i in range(0, len(paragraph), TARGET_CHUNK_CHARS)
    ]

    return [window for window in windows if window]


def chunk_text(text: str) -> list[str]:
    """
    Split a document into chunks near TARGET_CHUNK_CHARS while preserving
    paragraph boundaries where possible.
    """
    paragraphs = _split_paragraphs(text)

    paragraphs = [
        piece
        for paragraph in paragraphs
        for piece in _split_oversized(paragraph)
    ]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if (
            current
            and len(current) + 2 + len(paragraph) > TARGET_CHUNK_CHARS
        ):
            chunks.append(current)
            current = paragraph
        else:
            current = (
                f"{current}\n\n{paragraph}".strip()
                if current
                else paragraph
            )

    if current:
        chunks.append(current)

    # Avoid tiny orphan chunks.
    merged: list[str] = []

    for chunk in chunks:
        if merged and len(chunk) < MIN_CHUNK_CHARS:
            merged[-1] = f"{merged[-1]}\n\n{chunk}"
        else:
            merged.append(chunk)

    return merged or [text.strip()]


# ---------------------------------------------------------------------------
# Embedding cache
# ---------------------------------------------------------------------------

def _cache_key(drug_id: str, path: Path, text: str) -> str:
    digest = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()[:16]

    return f"{drug_id}:{path.name}:{digest}"


def _keys_path(cache_path: Path) -> Path:
    return cache_path.with_suffix(".keys.json")


def _load_cache(cache_path: Path) -> dict[str, list[float]]:
    keys_path = _keys_path(cache_path)

    if not cache_path.exists() or not keys_path.exists():
        return {}

    try:
        keys = json.loads(
            keys_path.read_text(encoding="utf-8")
        )

        payload = np.load(cache_path)
        vectors = payload["vectors"]

        if len(keys) != len(vectors):
            return {}

        return {
            key: vectors[i].tolist()
            for i, key in enumerate(keys)
        }

    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ):
        return {}


def _save_cache(
    cache_path: Path,
    cache: dict[str, list[float]],
) -> None:
    if not cache:
        return

    cache_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    keys = list(cache.keys())
    vectors = np.array(
        [cache[key] for key in keys],
        dtype=np.float32,
    )

    np.savez_compressed(
        cache_path,
        vectors=vectors,
    )

    _keys_path(cache_path).write_text(
        json.dumps(keys),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Dossier parsing
# ---------------------------------------------------------------------------

_FIELD_HEADER = re.compile(r"^[a-z0-9_]+:$")
_SECTION_HEADER = re.compile(r"^##\s+(.+)$")


def _slugify_field_name(title: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        title.strip().lower(),
    ).strip("_")


def _parse_raw_field_dump(text: str) -> dict[str, str]:
    """
    Parse the raw OpenFDA-style field format:

        field_name:
          value
          additional value
    """
    fields: dict[str, str] = {}

    current_key: str | None = None
    current_value: list[str] = []

    for line in text.splitlines():
        if (
            not line.startswith((" ", "\t"))
            and _FIELD_HEADER.match(line.strip())
        ):
            if current_key is not None:
                fields[current_key] = " ".join(
                    current_value
                ).strip()

            current_key = line.strip().rstrip(":")
            current_value = []

        elif current_key is not None and line.strip():
            current_value.append(line.strip())

    if current_key is not None:
        fields[current_key] = " ".join(
            current_value
        ).strip()

    return fields


def _parse_section_headers(text: str) -> dict[str, str]:
    """
    Parse the older:

        ## Section Title

    corpus format.
    """
    fields: dict[str, str] = {}

    current_key: str | None = None
    current_value: list[str] = []

    for line in text.splitlines():
        match = _SECTION_HEADER.match(line.strip())

        if match:
            if current_key is not None:
                fields[current_key] = " ".join(
                    current_value
                ).strip()

            current_key = _slugify_field_name(
                match.group(1)
            )
            current_value = []

        elif current_key is not None and line.strip():
            current_value.append(line.strip())

    if current_key is not None:
        fields[current_key] = " ".join(
            current_value
        ).strip()

    return fields


def parse_dossier(path: Path) -> Dossier:
    """
    Parse a structured dossier into a Dossier object.

    Supports a simple header block followed by `## Section` bodies.
    """
    dossier = Dossier(
        drug_id=path.stem,
        name=path.stem.title(),
    )

    section: str | None = None
    prose: list[str] = []
    bullets: list[str] = []

    def flush() -> None:
        if section is None:
            return

        dossier.sections[section] = {
            "prose": " ".join(" ".join(prose).split()),
            "bullets": list(bullets),
        }

    for raw in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw.strip()

        if line.startswith("## "):
            flush()

            section = line[3:].strip()
            prose = []
            bullets = []

        elif section is None:
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()

                if key == "name":
                    dossier.name = value
                elif key == "barcode":
                    dossier.barcode = value
                elif key == "headline":
                    dossier.headline = value
                elif key == "aliases":
                    dossier.aliases = [
                        alias.strip().lower()
                        for alias in value.split(",")
                        if alias.strip()
                    ]

        elif line.startswith("- "):
            bullets.append(line[2:].strip())

        elif line:
            prose.append(line)

    flush()

    return dossier


def load_dossiers(
    folder_path: str | None = None,
) -> dict[str, Dossier]:
    """
    Parse structured dossiers.

    Unlike the iOS branch's original implementation, this uses
    _iter_doc_files() so nested drug directories are supported too.
    """
    root = Path(
        folder_path or settings.drug_docs_path
    )

    if not root.is_dir():
        return {}

    return {
        drug_id: parse_dossier(path)
        for drug_id, path in _iter_doc_files(root)
    }


def parse_dossier_fields(
    drug_id: str,
    folder_path: str | None = None,
) -> dict[str, str]:
    """
    Read the raw drug document and return {field_name: value}.

    Supports both raw field dumps and ## Section documents.

    Used by personalization/scorer.py for HUD personalization.
    """
    root = Path(
        folder_path or settings.drug_docs_path
    )

    for drug_id_found, path in _iter_doc_files(root):
        if drug_id_found.lower() != drug_id.strip().lower():
            continue

        text = path.read_text(
            encoding="utf-8"
        )

        if re.search(r"(?m)^##\s+\S", text):
            return _parse_section_headers(text)

        return _parse_raw_field_dump(text)

    return {}


# ---------------------------------------------------------------------------
# Retrieval index construction
# ---------------------------------------------------------------------------

def _section_for_chunk(
    chunk_text_value: str,
    dossier: Dossier | None,
) -> str:
    """
    Best-effort section association for a generic raw document.

    Structured ## sections are handled directly by ingest_docs(). For raw
    field dumps, the field name is retained as the section metadata.
    """
    if dossier is None:
        return ""

    # The chunk may contain the field header itself.
    first_line = chunk_text_value.splitlines()[0].strip()

    if _FIELD_HEADER.match(first_line):
        return first_line.rstrip(":")

    return ""


def ingest_docs(
    folder_path: str | None = None,
) -> list[Chunk]:
    """
    Build and install the in-memory retrieval index.

    Preserves the llm-rag embedding cache and batch embedding pipeline while
    adding section metadata for section-aware retrieval.
    """
    root = Path(
        folder_path or settings.drug_docs_path
    )

    cache_path = Path(
        settings.embedding_cache_path
    )

    cache = _load_cache(cache_path)

    pending_texts: list[str] = []
    pending_meta: list[
        tuple[str, str, str]
    ] = []

    ready: list[Chunk] = []

    dossiers = load_dossiers(str(root))

    for drug_id, path in _iter_doc_files(root):
        raw = path.read_text(
            encoding="utf-8"
        )

        # Structured ## Section documents:
        # use the section as the natural semantic unit.
        dossier = dossiers.get(drug_id)

        if dossier and dossier.sections:
            for section, body in dossier.sections.items():
                parts: list[str] = []

                if body["prose"]:
                    parts.append(body["prose"])

                parts.extend(
                    bullet
                    if bullet.endswith(
                        (".", "!", "?")
                    )
                    else f"{bullet}."
                    for bullet in body["bullets"]
                )

                text = " ".join(parts).strip()

                if not text:
                    continue

                # Include section title in the embedding so queries such as
                # "what are the side effects?" naturally favor that section.
                embedding_input = (
                    f"{dossier.name} "
                    f"{section}. "
                    f"{text}"
                )

                key = _cache_key(
                    drug_id,
                    path,
                    embedding_input,
                )

                if key in cache:
                    ready.append(
                        Chunk(
                            drug_id=drug_id,
                            section=section,
                            text=text,
                            embedding=cache[key],
                        )
                    )
                else:
                    pending_texts.append(
                        embedding_input
                    )
                    pending_meta.append(
                        (
                            drug_id,
                            section,
                            key,
                        )
                    )

            continue

        # Generic/raw documents:
        # retain the robust chunking and embedding cache from llm-rag.
        for text in chunk_text(raw):
            section = _section_for_chunk(
                text,
                dossier,
            )

            key = _cache_key(
                drug_id,
                path,
                text,
            )

            if key in cache:
                ready.append(
                    Chunk(
                        drug_id=drug_id,
                        section=section,
                        text=text,
                        embedding=cache[key],
                    )
                )
            else:
                pending_texts.append(text)
                pending_meta.append(
                    (
                        drug_id,
                        section,
                        key,
                    )
                )

    if pending_texts:
        vectors = embed_texts(
            pending_texts
        )

        for (
            (drug_id, section, key),
            embedding_input,
            vector,
        ) in zip(
            pending_meta,
            pending_texts,
            vectors,
        ):
            cache[key] = vector

            # For structured sections, remove the artificial
            # "drug + section" prefix from the text handed to the LLM.
            if section and (
                embedding_input.startswith(
                    f"{dossiers[drug_id].name} {section}. "
                )
            ):
                prefix = (
                    f"{dossiers[drug_id].name} "
                    f"{section}. "
                )
                text = embedding_input[
                    len(prefix):
                ]
            else:
                text = embedding_input

            ready.append(
                Chunk(
                    drug_id=drug_id,
                    section=section,
                    text=text,
                    embedding=vector,
                )
            )

        _save_cache(
            cache_path,
            cache,
        )

    load(ready)

    return ready