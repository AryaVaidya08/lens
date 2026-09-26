from tests.auth_util import login


def test_summary_reflects_seeded_expert_tier(client):
    headers, _ = login(client, "hcp_002")
    resp = client.get("/drug/lorazepam/summary", params={"hcp_id": "hcp_002"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "expert"
    assert len(body["bullets"]) > 0


def test_summary_new_hcp_gets_new_tier_and_different_content(client):
    expert, _ = login(client, "hcp_002")
    newbie, _ = login(client, "hcp_003")
    expert_resp = client.get("/drug/lorazepam/summary", params={"hcp_id": "hcp_002"}, headers=expert)
    new_resp = client.get("/drug/lorazepam/summary", params={"hcp_id": "hcp_003"}, headers=newbie)
    assert new_resp.json()["tier"] == "new"
    assert new_resp.json()["bullets"] != expert_resp.json()["bullets"]


def test_summary_unknown_drug_returns_404(client):
    headers, _ = login(client, "hcp_001")
    resp = client.get("/drug/not_a_real_drug/summary", params={"hcp_id": "hcp_001"}, headers=headers)
    assert resp.status_code == 404
