import uuid

import app.routes.drug as drug_route
from tests.test_auth_hardening import _register


def test_full_scan_ask_rescan_flow(client, monkeypatch):
    # 1. iOS detects a package via barcode.
    detect_resp = client.post("/detect", json={"barcode": "0363323012345", "ocr_text": None})
    assert detect_resp.status_code == 200
    drug_id = detect_resp.json()["drug_id"]
    assert drug_id == "adderall"

    # Fresh clinician so this flow does not collide with Sofia's adderall loop.
    created = _register(client, email="e2e.%s@hospital.example" % uuid.uuid4().hex[:8])
    assert created.status_code == 200, created.text
    hcp_id = created.json()["hcp_id"]
    headers = {"Authorization": "Bearer " + created.json()["session_token"]}

    # 2. First summary: should be "new" tier.
    summary1 = client.get(
        f"/drug/{drug_id}/summary",
        params={"hcp_id": hcp_id},
        headers=headers,
    ).json()
    assert summary1["tier"] == "new"

    # 3. Voice follow-up question, grounded in the real RAG index — mock the
    #    LLM call itself so this test has no network/API-key dependency.
    monkeypatch.setattr(
        drug_route,
        "retrieve",
        lambda drug_id, query, specialty=None: ["Mock dossier snippet about this drug."],
    )
    monkeypatch.setattr(
        drug_route,
        "generate_answer",
        lambda query, context, tier="new", specialty=None: f"Mock answer using {len(context)} sources.",
    )
    ask_resp = client.post(
        f"/drug/{drug_id}/ask",
        json={"hcp_id": hcp_id, "query": "What is this used for?"},
        headers=headers,
    )
    assert ask_resp.status_code == 200
    assert "answer_text" in ask_resp.json()

    # 4. Log engagement twice (crosses the "expert" threshold of 2).
    log_resp = None
    for _ in range(2):
        log_resp = client.post(
            "/engagement/log",
            json={"hcp_id": hcp_id, "drug_id": drug_id},
            headers=headers,
        )
        assert log_resp.status_code == 200
    assert log_resp.json()["touch_count"] == 2

    # 5. Second summary: same HCP, same drug, must now be visibly different.
    summary2 = client.get(
        f"/drug/{drug_id}/summary",
        params={"hcp_id": hcp_id},
        headers=headers,
    ).json()
    assert summary2["tier"] == "expert"
    assert summary2["bullets"] != summary1["bullets"]

    # 6. Profile now reflects the updated tier too.
    profile_resp = client.get(f"/profile/{hcp_id}", headers=headers)
    assert profile_resp.json()["familiarity"][drug_id] == "expert"
