from tests.auth_util import login


def test_get_profile_known_hcp_includes_seeded_familiarity(client):
    headers, _ = login(client, "hcp_002")
    resp = client.get("/profile/hcp_002", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["hcp_id"] == "hcp_002"
    assert body["specialty"]
    assert body["familiarity"]["lorazepam"] == "expert"


def test_get_profile_unknown_hcp_returns_404(client):
    headers, _ = login(client, "hcp_001")
    resp = client.get("/profile/not_a_real_hcp", headers=headers)
    assert resp.status_code in {403, 404}
