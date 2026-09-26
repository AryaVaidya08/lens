"""
Drug detection resolution endpoint.
"""

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


class DetectRequest(BaseModel):
    barcode: Optional[str] = Field(default=None, max_length=128)
    ocr_text: Optional[str] = Field(default=None, max_length=20000)


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _match_barcode(barcode: str, drugs: list) -> Optional[dict]:
    raw = barcode.strip()
    if not raw:
        return None
    for drug in drugs:
        stored = drug.get("barcode") or ""
        if stored and stored == raw:
            return drug
    compact = _digits(raw)
    if not compact:
        return None
    for drug in drugs:
        stored = drug.get("barcode") or ""
        if stored and _digits(stored) == compact:
            return drug
    return None


def _match_ocr(ocr_text: str, drugs: list) -> Optional[dict]:
    text = ocr_text.lower()
    dossiers = load_dossiers(settings.drug_docs_path)

    for drug in drugs:
        names = [drug["name"].lower(), str(drug["_id"]).lower()]
        dossier = dossiers.get(drug["_id"])
        if dossier:
            names.extend(dossier.aliases)
        if any(name and name in text for name in names):
            return drug

    words = _TOKEN.findall(text)
    by_name = {drug["name"].lower(): drug for drug in drugs}
    for word in words:
        close = difflib.get_close_matches(word, list(by_name.keys()), n=1, cutoff=_FUZZY_CUTOFF)
        if close:
            return by_name[close[0]]
    return None


@router.post("")
def detect_drug(payload: DetectRequest, db: Database = Depends(get_db)) -> dict:
    drugs = list(db.drugs.find())
    drug = None
    if payload.barcode:
        drug = _match_barcode(payload.barcode, drugs)
    if drug is None and payload.ocr_text:
        drug = _match_ocr(payload.ocr_text, drugs)

    if drug is None:
        raise HTTPException(status_code=404, detail="No drug matched that barcode or text")
    return {"drug_id": drug["_id"], "name": drug["name"]}
