import uuid

from tests.test_auth_hardening import _register


def test_log_engagement_increments_touch_count(client):
    created = _register(client, email="eng.%s@hospital.example" % uuid.uuid4().hex[:8])
    assert created.status_code == 200, created.text
    hcp_id = created.json()["hcp_id"]
    headers = {"Authorization": "Bearer " + created.json()["session_token"]}
    resp1 = client.post(
        "/engagement/log",
        json={"hcp_id": hcp_id, "drug_id": "tylenol"},
        headers=headers,
    )
    assert resp1.status_code == 200
    count1 = resp1.json()["touch_count"]

    resp2 = client.post(
        "/engagement/log",
        json={"hcp_id": hcp_id, "drug_id": "tylenol"},
        headers=headers,
    )
    assert resp2.json()["touch_count"] == count1 + 1
