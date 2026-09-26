"""
Chart-vs-bottle flags for the scan HUD.

This is name matching against the imported chart and the drug dossier.
It is not a clinical decision, interaction checker, or allergy test.
"""

from __future__ import annotations

import re
from typing import Any

from app.retrieval.ingest import load_dossiers, parse_dossier_fields

_SPLIT = re.compile(r"[,;/\n]| and ", re.I)
_WORD = re.compile(r"[a-z0-9]+")
_STOP = {
    "none",
    "known",
    "nka",
    "nkda",
    "no",
    "not",
    "the",
    "and",
    "with",
    "for",
    "from",
    "daily",
    "once",
    "twice",
    "tablet",
    "tablets",
    "capsule",
    "oral",
    "mg",
    "ml",
    "bid",
    "tid",
    "qid",
    "prn",
    "use",
}

_INTERACTION_FIELDS = (
    "contraindications",
    "drug_interactions",
    "warnings",
    "warnings_and_cautions",
    "precautions",
)


def _items(text: str) -> list[str]:
    parts = [part.strip() for part in _SPLIT.split(text or "")]
    return [part for part in parts if part and part.lower() not in {"none", "n/a", "na"}]


def _tokens(text: str) -> set[str]:
    return {
        word
        for word in _WORD.findall((text or "").lower())
        if len(word) >= 4 and word not in _STOP
    }


def _overlap(left: set[str], right: set[str]) -> set[str]:
    hits = set()
    for a in left:
        for b in right:
            if a == b or (len(a) >= 5 and len(b) >= 5 and (a in b or b in a)):
                hits.add(a if len(a) >= len(b) else b)
    return hits


def _drug_terms(drug_id: str, name: str) -> set[str]:
    terms = _tokens(name) | _tokens(drug_id.replace("_", " "))
    dossier = load_dossiers().get(drug_id)
    if dossier:
        terms |= _tokens(dossier.name)
        for alias in dossier.aliases:
            terms |= _tokens(alias)
    fields = parse_dossier_fields(drug_id)
    for key in ("generic_name", "openfda_brand_names", "description"):
        terms |= _tokens(fields.get(key, "")[:400])
    return terms


def _interaction_blob(drug_id: str) -> str:
    fields = parse_dossier_fields(drug_id)
    return " ".join(fields.get(key, "") for key in _INTERACTION_FIELDS).lower()


def check_patient_chart(patient: dict[str, Any], drug_id: str, drug_name: str) -> dict[str, Any]:
    """Return HUD-sized flags for one owned patient and one resolved drug."""
    name = ("%s %s" % (patient.get("first_name") or "", patient.get("last_name") or "")).strip()
    drug_terms = _drug_terms(drug_id, drug_name)
    flags: list[str] = []

    for allergy in _items(str(patient.get("allergies") or "")):
        if allergy.lower() in {"none known", "no known allergies", "nka", "nkda"}:
            continue
        hits = _overlap(_tokens(allergy), drug_terms)
        if hits:
            flags.append("Allergy list mentions %s." % allergy)

    blob = _interaction_blob(drug_id)
    for med in _items(str(patient.get("current_medications") or "")):
        if med.lower() in {"none", "none known"}:
            continue
        med_terms = _tokens(med)
        if _overlap(med_terms, drug_terms):
            flags.append("Already on the chart: %s." % med)
            continue
        mentioned = [token for token in med_terms if re.search(r"\b%s\b" % re.escape(token), blob)]
        if mentioned:
            flags.append("Dossier interaction text mentions %s." % med)

    if flags:
        status = "flag"
        headline = "Chart flag for %s" % (name or "this patient")
    else:
        status = "clear"
        headline = "No name match on %s's allergy or med list" % (name.split()[0] if name else "this patient")

    return {
        "status": status,
        "patient_id": patient.get("_id") or "",
        "patient_name": name,
        "headline": headline,
        "flags": flags[:4],
        "disclaimer": "Name match against the imported chart and dossier. Not a clinical decision.",
    }
