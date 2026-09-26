"""
Demo data seeding.

Populates 3-4 mock HCPs and a handful of mock drugs before the demo, so
personalization has real starting state to show a delta against. Run
once at backend startup (or via a standalone script) before the demo.

Owned by: Content & demo lane.
"""


def seed() -> None:
    """
    Inserts mock HCPs, Drugs, and (optionally) a couple of pre-existing
    Engagement rows, so the "second scan looks different" story can be
    demoed without needing two live scans of the same drug.

    TODO: implement
    """
    # TODO: implement
    raise NotImplementedError
