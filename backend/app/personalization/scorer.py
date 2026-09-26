"""
Familiarity scoring.

The same HCP scanning the same drug should visibly get a more advanced
answer over repeated interactions.

Familiarity is calculated before the current scan is logged:
    scan 1 -> new
    scan 2 -> returning
    scan 3+ -> expert
"""

from __future__ import annotations

from pymongo.database import Database

from app.retrieval.ingest import parse_dossier_fields


# HUD is rendered before the current scan is logged.
RETURNING_AT = 1
EXPERT_AT = 2

TIERS = ("new", "returning", "expert")


# Ordered by priority; first present field wins. Covers both prescription
# SPL field names and OTC drug-facts field names because the corpus mixes both.
_TIER_FIELD_PRIORITY: dict[str, list[str]] = {
    "new": [
        "indications_and_usage",
        "purpose",
        "description",
    ],
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


def tier_for_touch_count(touch_count: int) -> str:
    """Map an existing touch count to the familiarity tier."""
    if touch_count >= EXPERT_AT:
        return "expert"
    if touch_count >= RETURNING_AT:
        return "returning"
    return "new"


def score_familiarity(
    hcp_id: str,
    drug_id: str,
    db: Database,
) -> str:
    """
    Return the HCP's current familiarity tier for a drug.

    The engagement count represents interactions that have already happened;
    the current scan is logged separately after the HUD/answer is generated.
    """
    row = db.engagements.find_one(
        {
            "hcp_id": hcp_id,
            "drug_id": drug_id,
        }
    )

    touch_count = row.get("touch_count", 0) if row else 0

    return tier_for_touch_count(touch_count)


def _truncate(
    text: str,
    max_chars: int = _MAX_BULLET_CHARS,
) -> str:
    """Keep HUD summary bullets short enough to display cleanly."""
    if len(text) <= max_chars:
        return text

    cut = text[:max_chars]
    last_space = cut.rfind(" ")

    if last_space > max_chars * 0.6:
        cut = cut[:last_space]

    return cut.rstrip(".,; ") + "..."


def build_summary_content(
    drug_id: str,
    tier: str,
) -> tuple[str, list[str]]:
    """
    Select the most useful dossier fields for the current familiarity tier.

    Returns:
        (headline, bullets)
    """
    fields = parse_dossier_fields(drug_id)

    headline = _TIER_HEADLINES.get(
        tier,
        "Overview",
    )

    bullets: list[str] = []

    for field_name in _TIER_FIELD_PRIORITY.get(tier, []):
        value = fields.get(field_name)

        if value:
            bullets.append(_truncate(value))

        if len(bullets) >= 3:
            break

    if not bullets:
        bullets = [
            "No additional information available for this drug yet."
        ]

    return headline, bullets