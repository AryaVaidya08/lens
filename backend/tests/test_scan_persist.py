from app.db.database import get_database
from tests.auth_util import login


def test_chart_check_and_scan_engagement_persist(client):
    headers, _ = login(client, "hcp_001")
    elena = client.get("/profile/hcp_001/patients/pat_001", headers=headers).json()["patient"]
    assert "amphet" in elena["allergies"].lower()
    assert elena.get("birth_date") == "1972-03-14"

    summary = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": "hcp_001", "patient_id": "pat_001"},
        headers=headers,
    ).json()
    assert summary["patient_check"]["status"] == "flag"
    assert "access_prefill" not in summary

    logged = client.post(
        "/engagement/log",
        json={"hcp_id": "hcp_001", "drug_id": "biofreeze", "patient_id": "pat_001"},
        headers=headers,
    )
    assert logged.status_code == 200
    db = get_database()
    engagement = db.engagements.find_one({"_id": "hcp_001:biofreeze"})
    assert engagement["last_patient_id"] == "pat_001"

    assert (
        client.post(
            "/engagement/log",
            json={"hcp_id": "hcp_001", "drug_id": "biofreeze", "patient_id": "pat_003"},
            headers=headers,
        ).status_code
        == 404
    )
