"""
Drug detection resolution endpoint.

Owned by: Backend & data lane (contract), AR & detection lane (client-side
capture that feeds this endpoint).
"""

import re
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Drug

router = APIRouter(prefix="/detect", tags=["detect"])

_FUZZY_MATCH_THRESHOLD = 0.75
_WHOLE_WORD_SCORE = 0.95


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _best_name_match(ocr_text: str, drugs: list[Drug]) -> Drug | None:
    lowered = ocr_text.lower()
    tokens = set(_tokenize(ocr_text))

    best_score = -1.0
    best_position = len(lowered) + 1
    best_drug: Drug | None = None

    for drug in drugs:
        name_lower = drug.name.lower()
        name_tokens = _tokenize(drug.name)

        # A whole-word match on every token of the drug's name (not just a
        # loose substring — "a" is a substring of "Advil" but shouldn't
        # confidently match it) beats a fuzzy ratio. Real packaging OCR
        # often contains both the brand and the generic name as separate
        # words, so ties are broken by whichever name appears earliest in
        # the text (packaging conventionally puts the brand first/largest).
        if name_tokens and all(token in tokens for token in name_tokens):
            score = _WHOLE_WORD_SCORE
            position = lowered.find(name_lower)
            if position == -1:
                position = lowered.find(name_tokens[0])
        else:
            score = SequenceMatcher(None, name_lower, lowered).ratio()
            for token in tokens:
                score = max(score, SequenceMatcher(None, name_lower, token).ratio())
            position = len(lowered) + 1  # no positional signal; sort after real matches

        if (score, -position) > (best_score, -best_position):
            best_score, best_position, best_drug = score, position, drug

    if best_drug is not None and best_score >= _FUZZY_MATCH_THRESHOLD:
        return best_drug
    return None


@router.post("")
def detect_drug(payload: dict, db: Session = Depends(get_db)) -> dict:
    """
    Takes a decoded barcode string or OCR text from the iOS app and
    resolves it to a known drug.

    Contract:
      <- { "barcode": str | None, "ocr_text": str | None }
      -> { "drug_id": str, "name": str }
    """
    barcode = payload.get("barcode")
    ocr_text = payload.get("ocr_text")

    if barcode:
        drug = db.query(Drug).filter(Drug.barcode == barcode).first()
        if drug:
            return {"drug_id": drug.id, "name": drug.name}

    if ocr_text and ocr_text.strip():
        match = _best_name_match(ocr_text, db.query(Drug).all())
        if match:
            return {"drug_id": match.id, "name": match.name}

    raise HTTPException(status_code=404, detail="Could not resolve a drug from the given barcode/OCR text.")
