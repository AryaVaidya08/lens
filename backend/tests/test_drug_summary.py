import pytest

from app.db.database import init_db
from app.db.seed import seed


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_summary_reflects_seeded_expert_tier(client):
    resp = client.get("/drug/ibuprofen/summary", params={"hcp_id": "hcp_amara"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "expert"
    assert len(body["bullets"]) > 0


def test_summary_new_hcp_gets_new_tier_and_different_content(client):
    expert_resp = client.get("/drug/ibuprofen/summary", params={"hcp_id": "hcp_amara"})
    new_resp = client.get("/drug/ibuprofen/summary", params={"hcp_id": "hcp_priya"})
    assert new_resp.json()["tier"] == "new"
    assert new_resp.json()["bullets"] != expert_resp.json()["bullets"]


def test_summary_unknown_drug_returns_404(client):
    resp = client.get("/drug/not_a_real_drug/summary", params={"hcp_id": "hcp_amara"})
    assert resp.status_code == 404
