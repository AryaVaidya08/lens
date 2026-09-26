"""
Drug detection resolution endpoint.

Accepts a barcode or OCR text from the iOS app and resolves it against
the in-memory detect catalog.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.database import Database

from app.db.database import get_db
from app.detection.catalog import resolve

router = APIRouter(prefix="/detect", tags=["detect"])


class DetectRequest(BaseModel):
    barcode: Optional[str] = Field(default=None, max_length=128)
    ocr_text: Optional[str] = Field(default=None, max_length=20000)


@router.post("")
def detect_drug(
    payload: DetectRequest,
    db: Database = Depends(get_db),
) -> dict:
    """
    Takes a decoded barcode string or OCR text from the iOS app and
    resolves it to a known drug.
    """
    drug = resolve(payload.barcode, payload.ocr_text, db)
    if drug is None:
        raise HTTPException(
            status_code=404,
            detail="No drug matched that barcode or text",
        )
    return {
        "drug_id": drug.drug_id,
        "name": drug.name,
    }
