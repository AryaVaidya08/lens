"""Second-pass hostile cases: sessions, mass assignment, clinic steal, extras."""

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.clinic.ingest import parse_clinic_record
from app.clinic.sync import sync_clinic_records
from app.db.mongo import get_database
from app.db.passwords import hash_token
from app.main import app
from app.routes import auth as auth_routes
from tests.auth_util import login
from tests.test_auth_hardening import _register


def test_forged_truncated_long_and_query_tokens_are_rejected():
    with TestClient(app) as client:
        created = _register(client).json()
        token = created["session_token"]
        path = "/profile/" + created["hcp_id"]
        assert client.get(path, headers={"Authorization": "Bearer forgedtoken"}).status_code == 401
        assert client.get(path, headers={"Authorization": "Bearer " + token[:8]}).status_code == 401
        assert client.get(path, headers={"Authorization": "Bearer " + ("A" * 200)}).status_code == 401
        assert client.get(path, headers={"Authorization": "Bearer " + token + "\x00"}).status_code == 401
        assert client.get(path, headers={"Authorization": "Basic " + token}).status_code == 401
        assert client.get(path, params={"token": token, "session_token": token}).status_code == 401
        real = {"Authorization": "Bearer " + token}
        other = _register(client).json()
        assert client.get("/profile/" + other["hcp_id"], headers=real).status_code == 403


def test_register_and_profile_reject_privilege_and_operator_fields():
    with TestClient(app) as client:
        sneaky = {
            "first_name": "Jordan",
            "last_name": "Lee",
            "email": "priv.%s@hospital.example" % uuid.uuid4().hex[:8],
            "password": "secret12",
            "professional_role": "Physician",
            "specialty": "Cardiology",
            "patient_ids": ["pat_001"],
            "password_hash": "stolen",
            "recovery_hash": "stolen",
            "is_admin": True,
            "_id": "hcp_001",
        }
        assert client.post("/auth/register", json=sneaky).status_code == 422
        created = _register(client).json()
        headers = {"Authorization": "Bearer " + created["session_token"]}
        assert created["patient_ids"] == []
        assert created["hcp_id"] != "hcp_001"
        assert "password_hash" not in created
        poisoned = client.patch(
            "/profile/" + created["hcp_id"],
            json={"patient_ids": ["pat_001"], "password_hash": "x", "specialty": "Cardiology"},
            headers=headers,
        )
        assert poisoned.status_code == 422
        operators = client.patch(
            "/profile/" + created["hcp_id"],
            json={"$set": {"specialty": "Hacked"}, "specialty": {"$gt": ""}},
            headers=headers,
        )
        assert operators.status_code == 422
        ok = client.patch(
            "/profile/" + created["hcp_id"],
            json={"specialty": "Geriatric Medicine"},
            headers=headers,
        )
        assert ok.status_code == 200
        assert ok.json()["specialty"] == "Geriatric Medicine"
        assert ok.json()["patient_ids"] == []


def test_homoglyph_and_null_emails_are_rejected():
    with TestClient(app) as client:
        cyrillic = _register(client, email="\u0430very.kim@hospital.example")
        assert cyrillic.status_code == 422
        null_email = client.post(
            "/auth/register",
            json={
                "first_name": "Jordan",
                "last_name": "Lee",
                "email": "null\u0000@hospital.example",
                "password": "secret12",
                "professional_role": "Physician",
                "specialty": "Cardiology",
            },
        )
        assert null_email.status_code == 422


def test_poisoned_patient_ids_do_not_list_another_doctors_chart():
    with TestClient(app) as client:
        created = _register(client).json()
        headers = {"Authorization": "Bearer " + created["session_token"]}
        db = get_database()
        db.hcps.update_one({"_id": created["hcp_id"]}, {"$set": {"patient_ids": ["pat_001", "pat_003"]}})
        rows = client.get("/profile/%s/patients" % created["hcp_id"], headers=headers).json()["patients"]
        assert rows == []
        assert client.get("/patients/pat_001", headers=headers).status_code == 404
        assert client.get("/patients/pat_003", headers=headers).status_code == 404


def test_clinic_sync_cannot_overwrite_or_steal_another_chart(monkeypatch):
    with TestClient(app) as client:
        created = _register(client).json()
        thief = created["hcp_id"]
        headers = {"Authorization": "Bearer " + created["session_token"]}
        maya, _ = login(client)

        def fake_records():
            return [
                {
                    "_id": "pat_001",
                    "hcp_id": thief,
                    "first_name": "Stolen",
                    "last_name": "Chart",
                    "external_id": "X",
                    "source": "attack",
                    "age": 1,
                    "weight_kg": 1,
                    "sex": "",
                    "medical_history": "",
                    "allergies": "",
                    "current_medications": "",
                    "notes": "",
                }
            ]

        monkeypatch.setattr("app.clinic.sync.load_clinic_records", fake_records)
        sync_clinic_records(get_database(), hcp_id=thief)
        elena = client.get("/patients/pat_001", headers=maya).json()
        assert elena["first_name"] == "Elena"
        assert elena["hcp_id"] == "hcp_001"
        assert client.get("/patients/pat_001", headers=headers).status_code == 404
        other = client.post("/patients/sync", params={"hcp_id": "hcp_001"}, headers=headers)
        assert other.status_code == 200
        assert all(row["hcp_id"] == thief for row in other.json()["patients"])


def test_guessed_patient_ids_and_wrong_methods():
    with TestClient(app) as client:
        headers, _ = login(client, "hcp_002")
        for pid in ("pat_001", "pat_002", "pat_004", "pat_999", "{$gt:''}"):
            assert client.get("/patients/" + pid, headers=headers).status_code == 404
        assert client.get("/patients/pat_003", headers=headers).status_code == 200
        assert client.get("/auth/login").status_code == 405
        assert client.get("/detect").status_code == 405
        assert client.delete("/profile/hcp_002", headers=headers).status_code == 405
        assert client.put("/patients/pat_003", json={"first_name": "X"}, headers=headers).status_code == 405
        assert client.post("/health").status_code == 405
        assert client.post("/status").status_code == 405
        assert client.get("/health").json() == {"status": "ok"}


def test_detect_does_not_dump_accounts_and_rejects_huge_ocr():
    with TestClient(app) as client:
        body = client.post("/detect", json={"barcode": "0363323012345", "ocr_text": None}).json()
        assert set(body) == {"drug_id", "name"}
        assert "patient" not in json.dumps(body).lower()
        assert "hcp" not in json.dumps(body).lower()
        huge = client.post("/detect", json={"ocr_text": "x" * 20001})
        assert huge.status_code == 422
        headers, body = login(client)
        ask = client.post(
            "/drug/adderall/ask",
            json={"hcp_id": body["hcp_id"], "query": "q" * 2001},
            headers=headers,
        )
        assert ask.status_code == 422


def test_familiarity_and_engagement_stay_on_the_session_account():
    with TestClient(app) as client:
        maya, _ = login(client, "hcp_001")
        james, _ = login(client, "hcp_002")
        maya_view = client.get("/drug/lorazepam/summary", params={"hcp_id": "hcp_001"}, headers=maya).json()
        james_view = client.get("/drug/lorazepam/summary", params={"hcp_id": "hcp_002"}, headers=james).json()
        assert maya_view["tier"] == "new"
        assert james_view["tier"] in {"returning", "expert"}
        assert james_view["tier"] != maya_view["tier"]
        assert client.get("/drug/lorazepam/summary", params={"hcp_id": "hcp_002"}, headers=maya).status_code == 403
        spoof = client.post(
            "/engagement/log",
            json={"hcp_id": "hcp_001", "drug_id": "adderall", "touch_count": 99},
            headers=james,
        )
        assert spoof.status_code == 422


def test_old_recovery_and_superseded_reset_tickets_die():
    with TestClient(app) as client:
        created = _register(client).json()
        old_recovery = created["recovery_code"]
        headers = {"Authorization": "Bearer " + created["session_token"]}
        changed = client.post(
            "/auth/change-password",
            json={"current_password": "secret12", "new_password": "newerpass1"},
            headers=headers,
        )
        assert changed.status_code == 200
        assert (
            client.post(
                "/auth/forgot-password",
                json={"email": created["email"], "recovery_code": old_recovery},
            ).status_code
            == 401
        )
        fresh = created["email"]
        new_recovery = changed.json()["recovery_code"]
        first = client.post(
            "/auth/forgot-password",
            json={"email": fresh, "recovery_code": new_recovery},
        ).json()
        second = client.post(
            "/auth/forgot-password",
            json={"email": fresh, "recovery_code": new_recovery},
        ).json()
        assert first["reset_token"] != second["reset_token"]
        reused = client.post(
            "/auth/reset-password",
            json={
                "email": fresh,
                "reset_token": first["reset_token"],
                "new_password": "brandnew1",
            },
        )
        assert reused.status_code == 401
        ok = client.post(
            "/auth/reset-password",
            json={
                "email": fresh,
                "reset_token": second["reset_token"],
                "new_password": "brandnew1",
            },
        )
        assert ok.status_code == 200
        assert (
            client.post(
                "/auth/forgot-password",
                json={"email": fresh, "recovery_code": new_recovery},
            ).status_code
            == 401
        )
        lower = _register(client).json()
        assert (
            client.post(
                "/auth/forgot-password",
                json={"email": lower["email"], "recovery_code": lower["recovery_code"].lower()},
            ).status_code
            == 200
        )


def test_reset_expiry_boundary_and_change_password_rate_limit():
    auth_routes._ATTEMPTS.clear()
    with TestClient(app) as client:
        created = _register(client).json()
        started = client.post(
            "/auth/forgot-password",
            json={"email": created["email"], "recovery_code": created["recovery_code"]},
        ).json()
        db = get_database()
        db.password_resets.update_one(
            {"token_hash": hash_token(started["reset_token"])},
            {"$set": {"expires_at": datetime.now(timezone.utc)}},
        )
        exact = client.post(
            "/auth/reset-password",
            json={
                "email": created["email"],
                "reset_token": started["reset_token"],
                "new_password": "newpass12",
            },
        )
        assert exact.status_code == 401
        headers = {"Authorization": "Bearer " + created["session_token"]}
        for _ in range(8):
            assert (
                client.post(
                    "/auth/change-password",
                    json={"current_password": "wrongpass", "new_password": "newerpass1"},
                    headers=headers,
                ).status_code
                == 401
            )
        assert (
            client.post(
                "/auth/change-password",
                json={"current_password": "secret12", "new_password": "newerpass1"},
                headers=headers,
            ).status_code
            == 429
        )
    auth_routes._ATTEMPTS.clear()


def test_openapi_and_status_do_not_leak_secrets_or_mutate():
    with TestClient(app) as client:
        created = _register(client).json()
        spec = client.get("/openapi.json")
        assert spec.status_code == 200
        dumped = spec.text
        assert created["session_token"] not in dumped
        assert created["recovery_code"] not in dumped
        assert "password_hash" not in dumped
        before = client.get("/status").json()
        assert "session_token" not in before
        assert client.post("/status").status_code == 405
        assert client.get("/status").json()["indexed_chunks"] == before["indexed_chunks"]


def test_clinic_record_path_ids_are_dropped():
    assert parse_clinic_record(
        {"patient_id": "../../../etc/passwd", "hcp_id": "hcp_001", "first_name": "A", "last_name": "B"}
    ) is None
    assert parse_clinic_record(
        {"patient_id": "pat_x", "hcp_id": {"$gt": ""}, "first_name": "A", "last_name": "B"}
    ) is None
    assert parse_clinic_record(
        {"_id": {"$gt": ""}, "hcp_id": "hcp_001", "first_name": "A", "last_name": "B"}
    ) is None
