"""
In-memory detect catalog.

Built once after seed so POST /detect does not load Mongo or dossiers
on every camera frame.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Optional

from pymongo.database import Database

from app.config import settings
from app.retrieval.ingest import load_dossiers

_TOKEN = re.compile(r"[a-z0-9]+")
_FUZZY_CUTOFF = 0.72
_WHOLE_WORD_SCORE = 0.95
_WHOLE_WORD_MIN = 4
_GENERIC_OCR_WORDS = {
    "real",
    "oral",
    "plus",
    "extra",
    "daily",
    "tablet",
    "tablets",
    "capsule",
    "capsules",
    "cream",
    "spray",
    "gel",
    "solution",
}


@dataclass(frozen=True)
class DetectEntry:
    drug_id: str
    name: str
    names: tuple[str, ...]


_exact: dict[str, DetectEntry] = {}
_digits: dict[str, DetectEntry] = {}
_entries: list[DetectEntry] = []


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _digit_key(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _barcodes(drug: dict) -> list[str]:
    values = [drug.get("barcode") or ""]
    extra = drug.get("barcodes") or []
    if isinstance(extra, list):
        values.extend(str(item) for item in extra)
    return [value.strip() for value in values if value and str(value).strip()]


def _names_for(drug: dict, dossiers: dict) -> tuple[str, ...]:
    drug_id = str(drug["_id"])
    names = [str(drug.get("name") or ""), drug_id]
    dossier = dossiers.get(drug_id)
    if dossier:
        names.extend(dossier.aliases)
    return tuple(
        dict.fromkeys(
            name.strip().lower()
            for name in names
            if name and name.strip()
        )
    )


def load(db: Database) -> int:
    """Replace the catalog from the current drugs collection."""
    global _exact, _digits, _entries
    dossiers = load_dossiers(settings.drug_docs_path)
    exact: dict[str, DetectEntry] = {}
    digits: dict[str, DetectEntry] = {}
    entries: list[DetectEntry] = []
    for drug in db.drugs.find():
        entry = DetectEntry(
            drug_id=str(drug["_id"]),
            name=str(drug.get("name") or drug["_id"]),
            names=_names_for(drug, dossiers),
        )
        entries.append(entry)
        for stored in _barcodes(drug):
            exact[stored] = entry
            compact = _digit_key(stored)
            if compact:
                digits[compact] = entry
    _exact = exact
    _digits = digits
    _entries = entries
    return len(entries)


def ensure_loaded(db: Database) -> None:
    if not _entries:
        load(db)


def size() -> int:
    return len(_entries)


def match_barcode(barcode: str) -> Optional[DetectEntry]:
    raw = (barcode or "").strip()
    if not raw:
        return None
    hit = _exact.get(raw)
    if hit:
        return hit
    compact = _digit_key(raw)
    if not compact:
        return None
    return _digits.get(compact)


def match_ocr(ocr_text: str) -> Optional[DetectEntry]:
    lowered = (ocr_text or "").lower()
    tokens = set(_tokenize(ocr_text or ""))
    if not tokens:
        return None

    best: Optional[DetectEntry] = None
    best_score = -1.0
    best_position = len(lowered) + 1

    for entry in _entries:
        for name in entry.names:
            name_tokens = _tokenize(name)
            if (
                not name_tokens
                or len(name) < _WHOLE_WORD_MIN
                or name in _GENERIC_OCR_WORDS
                or not all(token in tokens for token in name_tokens)
            ):
                continue
            position = lowered.find(name)
            if position == -1:
                position = lowered.find(name_tokens[0])
            if (_WHOLE_WORD_SCORE, -position) > (best_score, -best_position):
                best_score = _WHOLE_WORD_SCORE
                best_position = position
                best = entry

    if best is not None:
        return best

    for entry in _entries:
        for name in entry.names:
            score = difflib.SequenceMatcher(None, name, lowered).ratio()
            for token in tokens:
                score = max(score, difflib.SequenceMatcher(None, name, token).ratio())
            if (score, 0) > (best_score, -best_position):
                best_score = score
                best_position = len(lowered) + 1
                best = entry

    if best is None or best_score < _FUZZY_CUTOFF:
        return None
    if any(name in lowered and len(name) >= 5 for name in best.names):
        return best
    return None


def resolve(barcode: str | None, ocr_text: str | None, db: Database) -> Optional[DetectEntry]:
    """Barcode wins. OCR runs only when barcode is missing or unmatched."""
    ensure_loaded(db)
    if barcode:
        hit = match_barcode(barcode)
        if hit:
            return hit
    if ocr_text:
        return match_ocr(ocr_text)
    return None
