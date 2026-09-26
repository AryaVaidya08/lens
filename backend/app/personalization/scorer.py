"""
Familiarity scoring.

This is the product logic the whole demo hinges on: the same HCP
scanning the same drug a second time should visibly get a more advanced
answer.

Owned by: Content & demo lane.
"""

from app.db.database import SessionLocal
from app.db.models import Engagement
from app.retrieval.ingest import parse_dossier_fields

# Ordered by priority; first present field wins. Covers both prescription
# SPL field names (indications_and_usage, ...) and OTC drug-facts field
# names (purpose, directions, ...) since the real corpus mixes both.
_TIER_FIELD_PRIORITY: dict[str, list[str]] = {
    "new": ["indications_and_usage", "purpose", "description"],
    "returning": [
        "dosage_and_administration",
        "directions",
        "warnings",
        "warnings_and_cautions",
        "precautions",
    ],
    "expert": [
        "drug_interactions",
        "adverse_reactions",
        "clinical_pharmacology",
        "clinical_studies",
        "mechanism_of_action",
        "nonclinical_toxicology",
    ],
}

_TIER_HEADLINES = {
    "new": "What it is",
    "returning": "Dosing & precautions",
    "expert": "Clinical profile",
}

_MAX_BULLET_CHARS = 220


def score_familiarity(hcp_id: str, drug_id: str) -> str:
    """
    Returns one of "new", "returning", "expert" based on the HCP's
    Engagement.touch_count for this drug. 0 -> new, 1-2 -> returning,
    3+ -> expert.
    """
    db = SessionLocal()
    try:
        row = (
            db.query(Engagement)
            .filter(Engagement.hcp_id == hcp_id, Engagement.drug_id == drug_id)
            .first()
        )
        touch_count = row.touch_count if row else 0
    finally:
        db.close()

    if touch_count >= 3:
        return "expert"
    if touch_count >= 1:
        return "returning"
    return "new"


def _truncate(text: str, max_chars: int = _MAX_BULLET_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > max_chars * 0.6:
        cut = cut[:last_space]
    return cut.rstrip(".,; ") + "..."


def build_summary_content(drug_id: str, tier: str) -> tuple[str, list[str]]:
    """
    Picks which dossier fields to surface for `tier` and returns
    (headline, bullets). Falls back to a generic placeholder bullet if
    none of the tier's preferred fields exist in this drug's dossier.
    """
    fields = parse_dossier_fields(drug_id)
    headline = _TIER_HEADLINES.get(tier, "Overview")

    bullets: list[str] = []
    for field_name in _TIER_FIELD_PRIORITY.get(tier, []):
        value = fields.get(field_name)
        if value:
            bullets.append(_truncate(value))
        if len(bullets) >= 3:
            break

    if not bullets:
        bullets = ["No additional information available for this drug yet."]

    return headline, bullets
