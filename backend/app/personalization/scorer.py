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

# Editorial display priorities for any signed-in specialty, not demo IDs.
# Only existing dossier text is shown; absent sections fall back to tier content.
_SPECIALTY_FIELDS = {
    "primary care": ["dosage_and_administration", "directions", "patient_counseling_information"],
    "cardiology": ["drug_interactions", "clinical_pharmacology", "adverse_reactions"],
    "endocrinology": ["clinical_pharmacology", "drug_interactions", "clinical_studies"],
    "pediatrics": ["pediatric_use", "use_in_specific_populations", "dosage_and_administration"],
    "geriatric medicine": ["geriatric_use", "use_in_specific_populations", "drug_interactions"],
    "obstetrics and gynecology": ["pregnancy", "lactation", "nursing_mothers", "use_in_specific_populations"],
    "psychiatry": ["drug_abuse_and_dependence", "drug_interactions", "adverse_reactions"],
    "nephrology": ["renal_impairment", "use_in_specific_populations", "clinical_pharmacology"],
    "oncology": ["clinical_studies", "drug_interactions", "adverse_reactions"],
    "neurology": ["adverse_reactions", "drug_interactions", "warnings_and_cautions"],
    "acute care": ["boxed_warning", "contraindications", "dosage_and_administration"],
    "surgery": ["contraindications", "warnings_and_cautions", "dosage_and_administration"],
    "pulmonary": ["warnings_and_cautions", "adverse_reactions", "dosage_and_administration"],
    "gastroenterology": ["adverse_reactions", "drug_interactions", "dosage_and_administration"],
    "infectious disease": ["warnings_and_cautions", "contraindications", "dosage_and_administration"],
    "pain": ["boxed_warning", "drug_abuse_and_dependence", "dosage_and_administration"],
    "pharmacy": ["dosage_and_administration", "drug_interactions", "patient_counseling_information"],
    "dermatology": ["adverse_reactions", "warnings", "dosage_and_administration"],
    "rehab": ["patient_counseling_information", "dosage_and_administration", "warnings"],
}

# Picker labels and common synonyms -> a dossier lens. Unknown values still
# use the primary-care lens so a new signup is never generic-only.
_SPECIALTY_ALIASES = {
    "primary care": "primary care",
    "family medicine": "primary care",
    "internal medicine": "primary care",
    "general practice": "primary care",
    "hospital medicine": "primary care",
    "preventive medicine": "primary care",
    "public health": "primary care",
    "occupational medicine": "primary care",
    "aerospace medicine": "primary care",
    "sports medicine": "rehab",
    "nursing": "primary care",
    "clinical social work": "psychiatry",
    "cardiology": "cardiology",
    "cardiovascular disease": "cardiology",
    "clinical cardiac electrophysiology": "cardiology",
    "interventional cardiology": "cardiology",
    "cardiothoracic surgery": "cardiology",
    "vascular surgery": "cardiology",
    "endocrinology": "endocrinology",
    "endocrinology, diabetes and metabolism": "endocrinology",
    "nutrition and dietetics": "endocrinology",
    "reproductive endocrinology and infertility": "endocrinology",
    "pediatrics": "pediatrics",
    "adolescent medicine": "pediatrics",
    "developmental-behavioral pediatrics": "pediatrics",
    "neonatology": "pediatrics",
    "pediatric cardiology": "pediatrics",
    "pediatric critical care": "pediatrics",
    "pediatric emergency medicine": "pediatrics",
    "pediatric endocrinology": "pediatrics",
    "pediatric gastroenterology": "pediatrics",
    "pediatric hematology and oncology": "pediatrics",
    "pediatric infectious disease": "pediatrics",
    "pediatric nephrology": "pediatrics",
    "pediatric pulmonology": "pediatrics",
    "pediatric rheumatology": "pediatrics",
    "pediatric surgery": "pediatrics",
    "child neurology": "pediatrics",
    "child and adolescent psychiatry": "pediatrics",
    "geriatric medicine": "geriatric medicine",
    "geriatric psychiatry": "geriatric medicine",
    "obstetrics and gynecology": "obstetrics and gynecology",
    "ob/gyn": "obstetrics and gynecology",
    "gynecologic oncology": "obstetrics and gynecology",
    "maternal-fetal medicine": "obstetrics and gynecology",
    "urogynecology": "obstetrics and gynecology",
    "midwifery": "obstetrics and gynecology",
    "psychiatry": "psychiatry",
    "addiction medicine": "psychiatry",
    "addiction psychiatry": "psychiatry",
    "psychology": "psychiatry",
    "behavioral health counseling": "psychiatry",
    "nephrology": "nephrology",
    "urology": "nephrology",
    "oncology": "oncology",
    "medical oncology": "oncology",
    "hematology": "oncology",
    "hematology and oncology": "oncology",
    "surgical oncology": "oncology",
    "radiation oncology": "oncology",
    "neurology": "neurology",
    "epilepsy": "neurology",
    "neuromuscular medicine": "neurology",
    "vascular neurology": "neurology",
    "neurosurgery": "neurology",
    "emergency medicine": "acute care",
    "urgent care": "acute care",
    "critical care medicine": "acute care",
    "medical toxicology": "acute care",
    "anesthesiology": "acute care",
    "trauma surgery": "acute care",
    "general surgery": "surgery",
    "colorectal surgery": "surgery",
    "ophthalmology": "surgery",
    "orthopedic surgery": "surgery",
    "otolaryngology (ent)": "surgery",
    "plastic surgery": "surgery",
    "transplant surgery": "surgery",
    "oral and maxillofacial surgery": "surgery",
    "pulmonology": "pulmonary",
    "sleep medicine": "pulmonary",
    "respiratory therapy": "pulmonary",
    "gastroenterology": "gastroenterology",
    "hepatology": "gastroenterology",
    "infectious disease": "infectious disease",
    "allergy and immunology": "infectious disease",
    "pain medicine": "pain",
    "hospice and palliative medicine": "pain",
    "clinical pharmacy": "pharmacy",
    "community pharmacy": "pharmacy",
    "dermatology": "dermatology",
    "rheumatology": "dermatology",
    "physical medicine and rehabilitation": "rehab",
    "physical therapy": "rehab",
    "occupational therapy": "rehab",
    "speech-language pathology": "rehab",
    "audiology": "rehab",
    "dentistry": "surgery",
    "optometry": "surgery",
    "podiatry": "surgery",
    "pathology": "oncology",
    "diagnostic radiology": "oncology",
    "interventional radiology": "oncology",
    "neuroradiology": "neurology",
    "nuclear medicine": "oncology",
    "medical genetics": "pediatrics",
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


def _normalized_specialty(specialty: str | None) -> str:
    return " ".join((specialty or "").casefold().split())


def resolve_specialty(specialty: str | None) -> tuple[str, list[str]] | None:
    """
    Map any stored HCP specialty to dossier sections.

    Uses the clinician's own specialty label. Demo accounts are not special-cased.
    """
    raw = " ".join((specialty or "").split())
    if not raw:
        return None
    key = _normalized_specialty(raw)
    if key in {"other", "other / not listed", "not listed"}:
        return (raw, list(_SPECIALTY_FIELDS["primary care"]))
    lens = _SPECIALTY_ALIASES.get(key)
    if lens is None and key in _SPECIALTY_FIELDS:
        lens = key
    if lens is None:
        matches = [
            (len(alias), dest)
            for alias, dest in _SPECIALTY_ALIASES.items()
            if alias in key
        ]
        if matches:
            matches.sort(reverse=True)
            lens = matches[0][1]
    if lens not in _SPECIALTY_FIELDS:
        lens = "primary care"
    return (raw, list(_SPECIALTY_FIELDS[lens]))


def specialty_section_keys(specialty: str | None) -> list[str]:
    """Dossier sections this specialty should prefer, or empty if unset."""
    resolved = resolve_specialty(specialty)
    return list(resolved[1]) if resolved else []


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
    specialty: str | None = None,
    compact: bool = True,
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
            bullets.append(value)

        if len(bullets) >= 3:
            break

    if not bullets:
        bullets = [
            "No additional information available for this drug yet."
        ]

    resolved = resolve_specialty(specialty)
    if resolved:
        label, priority = resolved
        headline = label
        tier_fields = _TIER_FIELD_PRIORITY.get(tier, [])
        # Prefer a specialty section that is not the first familiarity field.
        focus = next((key for key in priority if fields.get(key) and key not in tier_fields[:1]), None)
        if focus is None:
            focus = next((key for key in priority if fields.get(key)), None)
        if focus is None:
            # OTC labels often lack Rx sections; still surface a useful field.
            focus = next(
                (
                    key
                    for key in ("warnings", "dosage_and_administration", "directions")
                    if fields.get(key) and key not in tier_fields[:1]
                ),
                None,
            )
        if focus:
            selected: list[str] = []
            # Reserve room for a prominent label warning regardless of specialty.
            safety = next((key for key in ("boxed_warning", "contraindications", "warnings_and_cautions", "warnings") if fields.get(key)), None)
            tier_field = next((key for key in tier_fields if fields.get(key)), None)
            for key in (safety, tier_field, focus):
                if key and key not in selected:
                    selected.append(key)
            for key in tier_fields + priority:
                if len(selected) >= 3:
                    break
                if fields.get(key) and key not in selected:
                    selected.append(key)
            bullets = [fields[key] for key in selected]
    return headline, bullets