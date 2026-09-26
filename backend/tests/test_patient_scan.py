from app.personalization.patient_check import check_patient_chart
from tests.auth_util import login


def test_amphetamines_allergy_flags_adderall():
    check = check_patient_chart(
        {
            "_id": "pat_001",
            "first_name": "Elena",
            "last_name": "Vasquez",
            "allergies": "Penicillin, amphetamines",
            "current_medications": "Metformin 1000 mg BID",
        },
        "adderall",
        "Adderall",
    )
    assert check["status"] == "flag"
    assert check["patient_id"] == "pat_001"
    assert any("amphet" in flag.lower() for flag in check["flags"])


def test_empty_chart_is_clear():
    check = check_patient_chart(
        {
            "_id": "pat_002",
            "first_name": "Marcus",
            "last_name": "Hale",
            "allergies": "None known",
            "current_medications": "None",
        },
        "adderall",
        "Adderall",
    )
    assert check["status"] == "clear"
    assert check["flags"] == []


def test_summary_route_uses_owned_patient_only(client):
    headers, _ = login(client, "hcp_001")
    flagged = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": "hcp_001", "patient_id": "pat_001"},
        headers=headers,
    )
    assert flagged.status_code == 200
    body = flagged.json()
    assert body["patient_check"]["status"] == "flag"
    assert (
        client.get(
            "/drug/adderall/summary",
            params={"hcp_id": "hcp_001", "patient_id": "pat_003"},
            headers=headers,
        ).status_code
        == 404
    )
    none = client.get(
        "/drug/biofreeze/summary",
        params={"hcp_id": "hcp_001"},
        headers=headers,
    ).json()
    assert none["patient_check"] is None
