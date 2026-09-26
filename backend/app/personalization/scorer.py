"""
Familiarity scoring.

This is the product logic the whole demo hinges on: the same HCP
scanning the same drug a second time should visibly get a more advanced
answer. Likely to get walked through live in the pitch — keep this
short and readable even as a stub.

Owned by: Content & demo lane.
"""


def score_familiarity(hcp_id: str, drug_id: str) -> str:
    """
    Returns one of "new", "returning", "expert" based on the HCP's
    Engagement.touch_count for this drug.

    TODO: implement — e.g. 0 touches -> "new", 1-2 -> "returning",
    3+ -> "expert". Tune thresholds against the demo script so the tier
    change is visible within the number of scans you'll actually do live.
    """
    # TODO: implement
    raise NotImplementedError
