"""
Drug detection resolution endpoint.

Owned by: Backend & data lane (contract), AR & detection lane (client-side
capture that feeds this endpoint).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/detect", tags=["detect"])


@router.post("")
def detect_drug(payload: dict) -> dict:
    """
    Takes a decoded barcode string or OCR text from the iOS app and
    resolves it to a known drug.

    Contract:
      <- { "barcode": str | None, "ocr_text": str | None }
      -> { "drug_id": str, "name": str }

    TODO: implement — look up Drug.barcode first; fall back to a fuzzy
    match against Drug.name using ocr_text if no barcode match.
    """
    # TODO: implement
    raise NotImplementedError
