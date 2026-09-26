from uuid import uuid4

from app.db.database import get_database
from tests.auth_util import login


def test_chart_check_and_scan_access_case_persist(client):
    headers, _ = login(client, "hcp_001")
    synced = client.post("/patients/sync", headers=headers)
    assert synced.status_code == 200
    elena = client.get("/patients/pat_001", headers=headers).json()
    assert "amphet" in elena["allergies"].lower()
    assert elena.get("birth_date") == "1972-03-14"

    summary = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": "hcp_001", "patient_id": "pat_001"},
        headers=headers,
    ).json()
    assert summary["patient_check"]["status"] == "flag"
    prefill = summary["access_prefill"]
    assert prefill["medication"] == "Adderall"
    assert prefill["strength"]
    assert prefill["formulation"] == "tablet"

    case_id = str(uuid4())
    saved = client.put(
        "/patients/pat_001/medication-access/%s" % case_id,
        json={
            "medication": prefill["medication"],
            "strength": prefill["strength"],
            "formulation": prefill["formulation"],
            "indication": prefill["indication"],
            "medication_source": "Lens scan · Adderall",
            "patient_dob": elena["birth_date"],
            "prescriber": "Dr. Maya Patel",
        },
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["medication"] == "Adderall"
    assert body["strength"] == prefill["strength"]
    assert body["medication_source"].startswith("Lens scan")
    assert body["patient_id"] == "pat_001"
    assert body["hcp_id"] == "hcp_001"

    listed = client.get("/patients/pat_001/medication-access", headers=headers).json()["cases"]
    stored = next(row for row in listed if row["case_id"] == case_id)
    assert stored["medication"] == "Adderall"
    assert stored["strength"] == prefill["strength"]

    db = get_database()
    mongo = db.medication_access.find_one({"case_id": case_id})
    assert mongo is not None
    assert mongo["medication"] == "Adderall"
    assert mongo["hcp_id"] == "hcp_001"

    logged = client.post(
        "/engagement/log",
        json={"hcp_id": "hcp_001", "drug_id": "adderall", "patient_id": "pat_001"},
        headers=headers,
    )
    assert logged.status_code == 200
    engagement = db.engagements.find_one({"_id": "hcp_001:adderall"})
    assert engagement["last_patient_id"] == "pat_001"

    assert (
        client.post(
            "/engagement/log",
            json={"hcp_id": "hcp_001", "drug_id": "adderall", "patient_id": "pat_003"},
            headers=headers,
        ).status_code
        == 404
    )
