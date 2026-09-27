"""
The personalization loop at the API layer: detect -> summary -> log ->
summary again, plus ask staying inside the named drug's dossier.
"""

from tests.auth_util import login


def test_health_and_status(client):
    assert client.get("/health").json() == {"status": "ok"}
    status = client.get("/status").json()
    assert status["indexed_chunks"] >= 15
    assert status["detect_catalog"] >= 3
    assert status["llm"] in {"api", "offline-fallback"}
    assert status["database"] == "mongodb"
    assert status["mongodb_db"]
    assert status["accounts_collection"] == "hcps"
    assert status["mongodb_kind"] in {"atlas", "localhost", "mongomock", "other"}
    assert "mongodb_uri" not in status


def test_detect_barcode_ocr_and_unknown(client):
    assert client.post("/detect", json={"barcode": "0363323012345"}).json() == {
        "drug_id": "adderall",
        "name": "Adderall",
    }
    assert client.post("/detect", json={"ocr_text": "LORAZEPAM 1 mg"}).json()[
        "drug_id"
    ] == "lorazepam"
    assert client.post("/detect", json={"ocr_text": "Biofreeze gel"}).json()[
        "drug_id"
    ] == "biofreeze"
    assert client.post("/detect", json={"ocr_text": "unrelated carton"}).status_code == 404


def test_summary_advances_after_each_log(client):
    headers, _ = login(client, "hcp_003")
    first = client.get(
        "/drug/adderall/summary", params={"hcp_id": "hcp_003"}, headers=headers
    ).json()
    assert first["drug_id"] == "adderall"
    assert first["tier"] == "new"
    assert first["full_bullets"] == []
    assert first["summary_source"] in {"grok", "unavailable"}
    client.post(
        "/engagement/log",
        json={"hcp_id": "hcp_003", "drug_id": "adderall"},
        headers=headers,
    )
    second = client.get(
        "/drug/adderall/summary", params={"hcp_id": "hcp_003"}, headers=headers
    ).json()
    assert second["tier"] == "returning"
    assert second["full_bullets"] == []
    if first["summary_source"] == "grok":
        assert second["bullets"] != first["bullets"]
    client.post(
        "/engagement/log",
        json={"hcp_id": "hcp_003", "drug_id": "adderall"},
        headers=headers,
    )
    third = client.get(
        "/drug/adderall/summary", params={"hcp_id": "hcp_003"}, headers=headers
    ).json()
    assert third["tier"] == "expert"


def test_preseeded_expert_and_profile_shape(client):
    headers, _ = login(client, "hcp_002")
    summary = client.get(
        "/drug/lorazepam/summary", params={"hcp_id": "hcp_002"}, headers=headers
    ).json()
    assert summary["tier"] == "expert"
    profile = client.get("/profile/hcp_002", headers=headers).json()
    assert profile["hcp_id"] == "hcp_002"
    assert profile["name"] == "Dr. James Chen"
    assert profile["familiarity"]["lorazepam"] == "expert"


def test_ask_is_stored_in_mongo(client):
    headers, _ = login(client, "hcp_001")
    client.post(
        "/drug/adderall/ask",
        json={"hcp_id": "hcp_001", "query": "how should I dose this"},
        headers=headers,
    )
    body = client.get("/profile/hcp_001/chats", headers=headers).json()
    assert body["chats"]
    assert body["chats"][0]["drug_id"] == "adderall"
    assert "dose" in body["chats"][0]["question"]


def test_ask_stays_in_dossier_and_refuses_unknown(client):
    headers, _ = login(client, "hcp_001")
    dose = client.post(
        "/drug/adderall/ask",
        json={"hcp_id": "hcp_001", "query": "how should I dose this"},
        headers=headers,
    ).json()["answer_text"]
    assert "amphetamine" not in dose.lower()
    assert "couldn't generate" in dose.lower()
    unknown = client.post(
        "/drug/adderall/ask",
        json={"hcp_id": "hcp_001", "query": "qxv9 lunar dust protocol for zebras"},
        headers=headers,
    ).json()["answer_text"]
    assert "couldn't generate" in unknown.lower()
    leak = client.post(
        "/drug/biofreeze/ask",
        json={"hcp_id": "hcp_001", "query": "boxed warning opioids"},
        headers=headers,
    ).json()["answer_text"]
    assert "opioid" not in leak.lower()
