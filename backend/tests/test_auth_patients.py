from app.clinic.ingest import parse_clinic_record
from tests.auth_util import login


def test_register_login_and_profile_fields(client):
    created = client.post(
        "/auth/register",
        json={
            "first_name": "Avery",
            "last_name": "Kim",
            "email": "Avery.Kim@Hospital.example",
            "password": "secret12",
            "professional_role": "Nurse Practitioner",
            "specialty": "Family Medicine",
            "credentials": "NP",
            "organization": "Northside",
            "city": "Atlanta",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["hcp_id"].startswith("hcp_")
    assert body["name"] == "Avery Kim"
    assert body["email"] == "avery.kim@hospital.example"
    assert body["patient_ids"] == []
    assert body["session_token"]
    assert body["recovery_code"]
    assert "password_hash" not in body
    headers = {"Authorization": "Bearer " + body["session_token"]}

    dup = client.post(
        "/auth/register",
        json={
            "first_name": "Avery",
            "last_name": "Kim",
            "email": "avery.kim@hospital.example",
            "password": "secret12",
            "professional_role": "Nurse Practitioner",
            "specialty": "Family Medicine",
        },
    )
    assert dup.status_code == 409

    bad = client.post(
        "/auth/login",
        json={"email": "avery.kim@hospital.example", "password": "nope"},
    )
    assert bad.status_code == 401

    ok = client.post(
        "/auth/login",
        json={"email": "avery.kim@hospital.example", "password": "secret12"},
    )
    assert ok.status_code == 200
    assert ok.json()["hcp_id"] == body["hcp_id"]

    patched = client.patch(
        "/profile/" + body["hcp_id"],
        json={"specialty": "Geriatric Medicine", "credentials": "NP-C"},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["specialty"] == "Geriatric Medicine"
    assert patched.json()["credentials"] == "NP-C"


def test_password_reset_and_change_require_secrets(client):
    created = client.post(
        "/auth/register",
        json={
            "first_name": "Riley",
            "last_name": "Cho",
            "email": "riley.cho@hospital.example",
            "password": "oldpass12",
            "professional_role": "Physician",
            "specialty": "Cardiology",
        },
    ).json()
    recovery = created["recovery_code"]
    token = created["session_token"]

    stolen = client.post(
        "/auth/forgot-password",
        json={"email": "riley.cho@hospital.example", "recovery_code": "WRONGCODE1"},
    )
    assert stolen.status_code == 401
    missing = client.post(
        "/auth/forgot-password",
        json={"email": "nobody@hospital.example", "recovery_code": recovery},
    )
    assert missing.status_code == 401

    started = client.post(
        "/auth/forgot-password",
        json={"email": "riley.cho@hospital.example", "recovery_code": recovery},
    )
    assert started.status_code == 200
    assert started.json()["expires_in"] == 900
    reset_token = started.json()["reset_token"]

    reset = client.post(
        "/auth/reset-password",
        json={
            "email": "riley.cho@hospital.example",
            "reset_token": reset_token,
            "new_password": "newpass12",
        },
    )
    assert reset.status_code == 200
    assert reset.json()["recovery_code"] != recovery
    reused = client.post(
        "/auth/reset-password",
        json={
            "email": "riley.cho@hospital.example",
            "reset_token": reset_token,
            "new_password": "another12",
        },
    )
    assert reused.status_code == 401
    assert "already used" in reused.json()["detail"]
    assert client.get("/profile/" + created["hcp_id"], headers={"Authorization": "Bearer " + token}).status_code == 401
    assert client.post(
        "/auth/login",
        json={"email": "riley.cho@hospital.example", "password": "oldpass12"},
    ).status_code == 401
    headers, session = login_email(client, "riley.cho@hospital.example", "newpass12")
    changed = client.post(
        "/auth/change-password",
        json={"current_password": "newpass12", "new_password": "newerpass1"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert client.post(
        "/auth/login",
        json={"email": "riley.cho@hospital.example", "password": "newpass12"},
    ).status_code == 401


def test_password_reset_expires_after_15_minutes(client):
    from datetime import datetime, timedelta, timezone

    from app.db.mongo import get_database
    from app.db.passwords import hash_token

    created = client.post(
        "/auth/register",
        json={
            "first_name": "Sam",
            "last_name": "Ortiz",
            "email": "sam.ortiz@hospital.example",
            "password": "oldpass12",
            "professional_role": "Physician",
            "specialty": "Cardiology",
        },
    ).json()
    started = client.post(
        "/auth/forgot-password",
        json={
            "email": "sam.ortiz@hospital.example",
            "recovery_code": created["recovery_code"],
        },
    ).json()
    db = get_database()
    db.password_resets.update_one(
        {"token_hash": hash_token(started["reset_token"])},
        {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)}},
    )
    expired = client.post(
        "/auth/reset-password",
        json={
            "email": "sam.ortiz@hospital.example",
            "reset_token": started["reset_token"],
            "new_password": "newpass12",
        },
    )
    assert expired.status_code == 401
    assert "expired" in expired.json()["detail"]
    assert client.post(
        "/auth/login",
        json={"email": "sam.ortiz@hospital.example", "password": "oldpass12"},
    ).status_code == 200


def login_email(client, email, password):
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": "Bearer " + body["session_token"]}, body


def test_no_account_backdoors(client):
    assert client.get("/profile/hcp_001").status_code == 401
    assert client.get("/profile/hcp_001/patients").status_code == 401
    assert client.get("/patients/pat_001").status_code == 401
    assert client.post("/patients/sync").status_code == 401
    assert client.post("/engagement/log", json={"hcp_id": "hcp_001", "drug_id": "adderall"}).status_code == 401

    maya, _ = login(client, "hcp_001")
    james, _ = login(client, "hcp_002")
    assert client.get("/profile/hcp_002", headers=maya).status_code == 403
    assert client.get("/profile/hcp_002/patients", headers=maya).status_code == 403
    assert client.get("/patients/pat_003", headers=maya).status_code == 404
    chart = client.get("/patients/pat_003", headers=james)
    assert chart.status_code == 200
    assert chart.json()["last_name"] == "Shah"
    assert client.patch(
        "/profile/hcp_002",
        json={"specialty": "Hacked"},
        headers=maya,
    ).status_code == 403
    assert client.post(
        "/engagement/log",
        json={"hcp_id": "hcp_002", "drug_id": "adderall"},
        headers=maya,
    ).status_code == 403


def test_demo_login_and_clinic_imported_folders(client):
    headers, body = login(client, "hcp_001")
    assert body["hcp_id"] == "hcp_001"
    assert "pat_001" in body["patient_ids"]
    assert "pat_002" in body["patient_ids"]

    folders = client.get("/profile/hcp_001/patients", headers=headers).json()["patients"]
    names = {"%s %s" % (row["first_name"], row["last_name"]) for row in folders}
    assert "Elena Vasquez" in names
    assert "Marcus Hale" in names
    assert all(row["hcp_id"] == "hcp_001" for row in folders)
    elena = next(row for row in folders if row["patient_id"] == "pat_001")
    assert elena["source"] == "riverside-ehr"
    assert elena["external_id"] == "MRN-10482"
    assert elena["sex"] == "Female"

    james, _ = login(client, "hcp_002")
    rows = client.get("/profile/hcp_002/patients", headers=james).json()["patients"]
    assert [row["patient_id"] for row in rows] == ["pat_003"]


def test_patients_are_read_only_in_the_api(client):
    headers, _ = login(client)
    assert (
        client.post(
            "/patients",
            json={"hcp_id": "hcp_001", "first_name": "Nina", "last_name": "Cole"},
            headers=headers,
        ).status_code
        == 404
    )
    assert (
        client.patch(
            "/patients/pat_001",
            json={"first_name": "Elena", "last_name": "Vasquez"},
            headers=headers,
        ).status_code
        == 405
    )
    assert client.delete("/patients/pat_001", headers=headers).status_code == 405
    chart = client.get("/patients/pat_001", headers=headers)
    assert chart.status_code == 200
    assert chart.json()["first_name"] == "Elena"


def test_sync_refreshes_signed_in_doctor_only(client):
    headers, _ = login(client, "hcp_003")
    body = client.post("/patients/sync", headers=headers).json()
    assert body["imported"] == 1
    assert body["patients"][0]["patient_id"] == "pat_004"
    assert body["patients"][0]["hcp_id"] == "hcp_003"
    assert client.get("/patients/pat_missing", headers=headers).status_code == 404


def test_fhir_and_export_records_parse_to_the_same_shape():
    fhir = parse_clinic_record(
        {
            "resourceType": "Patient",
            "id": "MRN-9",
            "patient_id": "pat_fhir",
            "hcp_id": "hcp_001",
            "name": [{"family": "Ng", "given": ["Lina"]}],
            "gender": "female",
            "birthDate": "1990-01-01",
            "chart": {"weight_kg": 60, "allergies": "None"},
        }
    )
    export = parse_clinic_record(
        {
            "patient_id": "pat_export",
            "hcp_id": "hcp_001",
            "first_name": "Lina",
            "last_name": "Ng",
            "age": 20,
            "weight_kg": 60,
        }
    )
    assert fhir["first_name"] == "Lina"
    assert fhir["last_name"] == "Ng"
    assert fhir["external_id"] == "MRN-9"
    assert fhir["weight_kg"] == 60
    assert export["first_name"] == "Lina"
    assert parse_clinic_record({"first_name": "Missing", "last_name": "Owner"}) is None
