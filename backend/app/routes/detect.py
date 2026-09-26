"""
Drug detection resolution endpoint.

Owned by: Backend & data lane (contract), AR & detection lane (client-side
capture that feeds this endpoint).
"""

from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Drug

router = APIRouter(prefix="/detect", tags=["detect"])

_FUZZY_MATCH_THRESHOLD = 0.5


def _best_name_match(ocr_text: str, drugs: list[Drug]) -> Drug | None:
    needle = ocr_text.lower()
    best: tuple[float, Drug] | None = None
    for drug in drugs:
        score = SequenceMatcher(None, needle, drug.name.lower()).ratio()
        if needle in drug.name.lower() or drug.name.lower() in needle:
            score = max(score, 0.9)
        if best is None or score > best[0]:
            best = (score, drug)
    if best and best[0] >= _FUZZY_MATCH_THRESHOLD:
        return best[1]
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
