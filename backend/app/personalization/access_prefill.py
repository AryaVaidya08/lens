"""Best-effort prescription fields from a dossier so an access case is not blank."""

from __future__ import annotations

import re

from app.retrieval.ingest import parse_dossier_fields

_STRENGTH = re.compile(r"\b(\d+(?:\.\d+)?\s*mg)\b", re.I)
_FORMULATIONS = (
    ("tablets", "tablet"),
    ("tablet", "tablet"),
    ("capsules", "capsule"),
    ("capsule", "capsule"),
    ("gel", "gel"),
    ("cream", "cream"),
    ("spray", "spray"),
    ("solution", "solution"),
)


def _first_sentence(text: str, limit: int = 180) -> str:
    cleaned = " ".join((text or "").split())
    cleaned = re.sub(
        r"^(indications and usage|purpose|description)\s+",
        "",
        cleaned,
        flags=re.I,
    )
    if not cleaned:
        return ""
    cut = cleaned.split(". ")[0].strip(" .")
    if len(cut) > limit:
        cut = cut[:limit].rsplit(" ", 1)[0] + "..."
    return cut


def build_access_prefill(drug_id: str, name: str) -> dict[str, str]:
    fields = parse_dossier_fields(drug_id)
    how = fields.get("how_supplied") or ""
    dosage = fields.get("dosage_and_administration") or fields.get("directions") or ""
    description = fields.get("description") or ""
    indication = fields.get("indications_and_usage") or fields.get("purpose") or ""
    blob = " ".join((how, dosage, description, fields.get("route") or ""))
    strength = ""
    match = _STRENGTH.search(how) or _STRENGTH.search(dosage) or _STRENGTH.search(description)
    if match:
        amount, unit = match.group(1).lower().split()
        strength = "%s %s" % (amount, unit)
    formulation = ""
    lowered = blob.lower()
    for needle, label in _FORMULATIONS:
        if needle in lowered:
            formulation = label
            break
    return {
        "medication": name,
        "strength": strength,
        "formulation": formulation,
        "directions": "",
        "indication": _first_sentence(indication),
    }
