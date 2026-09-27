from tests.auth_util import login


def _create_patient(client, headers, hcp_id, **overrides):
    payload = {
        "first_name": "Jordan",
        "last_name": "Rivera",
        "age": 68,
        "sex": "F",
        "weight_kg": 82,
        "allergies": "sulfa drugs",
        "current_medications": "lisinopril",
    }
    payload.update(overrides)
    resp = client.post(f"/profile/{hcp_id}/patients", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["patient"]["patient_id"]


def test_ask_with_patient_id_passes_patient_context(client, monkeypatch):
    import app.routes.drug as drug_route

    maya, _ = login(client, "hcp_001")
    patient_id = _create_patient(client, maya, "hcp_001")

    seen = {}

    monkeypatch.setattr(
        drug_route,
        "retrieve",
        lambda drug_id, query, specialty=None: ["Dosing 5 mg. Interactions with stimulants."],
    )

    def fake_answer(query, context, tier="new", specialty=None, patient_context=None):
        seen["patient_context"] = patient_context
        return "ok"

    monkeypatch.setattr(drug_route, "generate_answer", fake_answer)

    resp = client.post(
        "/drug/adderall/ask",
        json={"hcp_id": "hcp_001", "query": "is this ok", "patient_id": patient_id},
        headers=maya,
    )
    assert resp.status_code == 200, resp.text
    assert seen["patient_context"] is not None
    assert "68yo" in seen["patient_context"]
    assert "sulfa drugs" in seen["patient_context"]
    assert "lisinopril" in seen["patient_context"]


def test_ask_without_patient_id_passes_no_patient_context(client, monkeypatch):
    import app.routes.drug as drug_route

    maya, _ = login(client, "hcp_001")

    seen = {}

    monkeypatch.setattr(
        drug_route,
        "retrieve",
        lambda drug_id, query, specialty=None: ["Dosing 5 mg."],
    )

    def fake_answer(query, context, tier="new", specialty=None, patient_context=None):
        seen["patient_context"] = patient_context
        return "ok"

    monkeypatch.setattr(drug_route, "generate_answer", fake_answer)

    resp = client.post(
        "/drug/adderall/ask",
        json={"hcp_id": "hcp_001", "query": "is this ok"},
        headers=maya,
    )
    assert resp.status_code == 200, resp.text
    assert seen["patient_context"] is None


def test_ask_rejects_patient_id_owned_by_another_hcp(client, monkeypatch):
    import app.routes.drug as drug_route

    maya, _ = login(client, "hcp_001")
    james, _ = login(client, "hcp_002")
    patient_id = _create_patient(client, maya, "hcp_001")

    monkeypatch.setattr(
        drug_route,
        "retrieve",
        lambda drug_id, query, specialty=None: ["Dosing 5 mg."],
    )
    monkeypatch.setattr(
        drug_route,
        "generate_answer",
        lambda *a, **k: "ok",
    )

    resp = client.post(
        "/drug/adderall/ask",
        json={"hcp_id": "hcp_002", "query": "is this ok", "patient_id": patient_id},
        headers=james,
    )
    assert resp.status_code == 404
