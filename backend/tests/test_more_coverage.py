"""Extra regression cases for profile writes, chart flags, and detect."""

from app.db.mongo import get_database
from app.db.seed import seed
from app.personalization.patient_check import check_patient_chart
from tests.auth_util import login


def test_seed_keeps_demo_bottle_barcodes(client):
    db = get_database()
    seed(db)
    adderall = db.drugs.find_one({"_id": "adderall"})
    assert "0363323012345" in (adderall.get("barcodes") or [])
    assert adderall["name"]


def test_profile_optional_fields_can_be_cleared_and_stay_cleared(client):
    headers, body = login(client, "hcp_001")
    hcp_id = body["hcp_id"]
    filled = client.patch(
        "/profile/" + hcp_id,
        json={"organization": "Temporary Clinic", "work_phone": "404-555-0100"},
        headers=headers,
    )
    assert filled.status_code == 200
    assert filled.json()["organization"] == "Temporary Clinic"
    cleared = client.patch(
        "/profile/" + hcp_id,
        json={"organization": "", "work_phone": ""},
        headers=headers,
    )
    assert cleared.status_code == 200
    row = get_database().hcps.find_one({"_id": hcp_id})
    assert row["organization"] == ""
    assert row["work_phone"] == ""
    seed(get_database())
    row = get_database().hcps.find_one({"_id": hcp_id})
    assert row["organization"] == ""
    assert row["work_phone"] == ""


def test_summary_without_patient_has_no_chart_check(client):
    headers, _ = login(client, "hcp_001")
    body = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": "hcp_001"},
        headers=headers,
    ).json()
    assert body["patient_check"] is None


def test_ativan_allergy_flags_lorazepam_scan():
    check = check_patient_chart(
        {
            "_id": "pat_j",
            "first_name": "Max",
            "last_name": "Cho",
            "allergies": "ativan",
            "current_medications": "None",
        },
        "lorazepam",
        "Lorazepam",
    )
    assert check["status"] == "flag"
    assert check["flags"]


def test_engagement_without_patient_does_not_invent_last_patient(client):
    headers, _ = login(client, "hcp_003")
    db = get_database()
    db.engagements.delete_one({"_id": "hcp_003:biofreeze"})
    logged = client.post(
        "/engagement/log",
        json={"hcp_id": "hcp_003", "drug_id": "biofreeze"},
        headers=headers,
    )
    assert logged.status_code == 200
    row = db.engagements.find_one({"_id": "hcp_003:biofreeze"})
    assert row["touch_count"] >= 1
    assert "last_patient_id" not in row or row.get("last_patient_id") in {None, ""}
