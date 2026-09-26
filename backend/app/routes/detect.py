"""
Drug detection resolution endpoint.

Accepts a barcode or OCR text from the iOS app and resolves it against
the MongoDB drug catalog and drug-reference dossiers.
"""

from __future__ import annotations

import difflib
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.database import Database

from app.config import settings
from app.db.database import get_db
from app.retrieval.ingest import load_dossiers

router = APIRouter(prefix="/detect", tags=["detect"])

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


class DetectRequest(BaseModel):
    barcode: Optional[str] = Field(default=None, max_length=128)
    ocr_text: Optional[str] = Field(default=None, max_length=20000)


def _digits(value: str) -> str:
    """Return only digits from a barcode."""
    return "".join(character for character in value if character.isdigit())


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _match_barcode(
    barcode: str,
    drugs: list[dict],
) -> Optional[dict]:
    """
    Match barcodes exactly first, then compare digit-only forms.

    The second pass handles OCR/scanner formatting differences such as
    hyphens or spaces.
    """
    raw = barcode.strip()

    if not raw:
        return None

    for drug in drugs:
        for stored in _barcodes(drug):
            if stored == raw:
                return drug

    compact = _digits(raw)

    if not compact:
        return None

    for drug in drugs:
        for stored in _barcodes(drug):
            if _digits(stored) == compact:
                return drug

    return None


def _barcodes(drug: dict) -> list[str]:
    values = [drug.get("barcode") or ""]
    extra = drug.get("barcodes") or []
    if isinstance(extra, list):
        values.extend(str(item) for item in extra)
    return [value.strip() for value in values if value and str(value).strip()]


def _match_ocr(
    ocr_text: str,
    drugs: list[dict],
) -> Optional[dict]:
    """
    Resolve OCR text using:

    1. Whole-word name/alias matches.
    2. Fuzzy matching against individual OCR tokens.
    3. Dossier aliases from the reference corpus.
    """
    lowered = ocr_text.lower()
    tokens = set(_tokenize(ocr_text))

    if not tokens:
        return None

    dossiers = load_dossiers(settings.drug_docs_path)

    def _names_for(drug: dict) -> list[str]:
        drug_id = str(drug["_id"])
        names = [str(drug.get("name") or ""), drug_id]
        dossier = dossiers.get(drug_id)
        if dossier:
            names.extend(dossier.aliases)
        return list(
            dict.fromkeys(
                name.strip().lower()
                for name in names
                if name and name.strip()
            )
        )

    best_drug: Optional[dict] = None
    best_score = -1.0
    best_position = len(lowered) + 1

    for drug in drugs:
        for name in _names_for(drug):
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
                best_drug = drug

    if best_drug is not None:
        return best_drug

    for drug in drugs:
        for name in _names_for(drug):
            score = difflib.SequenceMatcher(None, name, lowered).ratio()
            for token in tokens:
                score = max(
                    score,
                    difflib.SequenceMatcher(None, name, token).ratio(),
                )
            if (score, 0) > (best_score, -best_position):
                best_score = score
                best_position = len(lowered) + 1
                best_drug = drug

    if best_drug is None or best_score < _FUZZY_CUTOFF:
        return None
    names = _names_for(best_drug)
    if any(name in lowered and len(name) >= 5 for name in names):
        return best_drug
    return None


@router.post("")
def detect_drug(
    payload: DetectRequest,
    db: Database = Depends(get_db),
) -> dict:
    """
    Takes a decoded barcode string or OCR text from the iOS app and
    resolves it to a known drug.

    Request:
        {
            "barcode": str | None,
            "ocr_text": str | None
        }

    Response:
        {
            "drug_id": str,
            "name": str
        }
    """
    drugs = list(db.drugs.find())

    drug = None

    if payload.barcode:
        drug = _match_barcode(payload.barcode, drugs)

    if drug is None and payload.ocr_text:
        drug = _match_ocr(payload.ocr_text, drugs)

    if drug is None:
        raise HTTPException(
            status_code=404,
            detail="No drug matched that barcode or text",
        )

    return {
        "drug_id": drug["_id"],
        "name": drug["name"],
    }