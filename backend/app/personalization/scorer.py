"""
Familiarity scoring.

The same HCP scanning the same drug a second time should visibly get a
more advanced answer. Thresholds are tight so a live demo shows the jump.
"""

from pymongo.database import Database

# HUD is rendered *before* the scan is logged, so scan 1 is "new",
# scan 2 is "returning", scan 3 is "expert".
RETURNING_AT = 1
EXPERT_AT = 2

TIERS = ("new", "returning", "expert")


def tier_for_touch_count(touch_count: int) -> str:
    if touch_count >= EXPERT_AT:
        return "expert"
    if touch_count >= RETURNING_AT:
        return "returning"
    return "new"


def score_familiarity(hcp_id: str, drug_id: str, db: Database) -> str:
    row = db.engagements.find_one({"hcp_id": hcp_id, "drug_id": drug_id})
    return tier_for_touch_count(row["touch_count"] if row else 0)
