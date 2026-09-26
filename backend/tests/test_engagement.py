import pytest

from app.db.database import init_db
from app.db.seed import seed


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_log_engagement_increments_touch_count(client):
    resp1 = client.post("/engagement/log", json={"hcp_id": "hcp_priya", "drug_id": "tylenol"})
    assert resp1.status_code == 200
    count1 = resp1.json()["touch_count"]

    resp2 = client.post("/engagement/log", json={"hcp_id": "hcp_priya", "drug_id": "tylenol"})
    assert resp2.json()["touch_count"] == count1 + 1
