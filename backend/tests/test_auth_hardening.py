"""Hostile cases for signup, login, reset, and session-bound routes."""

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.routes import auth as auth_routes
from tests.auth_util import login


def _register(client, email=None, password="secret12", **extra):
    body = {
        "first_name": "Jordan",
        "last_name": "Lee",
        "email": email or ("user.%s@hospital.example" % uuid.uuid4().hex[:10]),
        "password": password,
        "professional_role": "Physician",
        "specialty": "Cardiology",
    }
    body.update(extra)
    return client.post("/auth/register", json=body)


def test_register_rejects_empty_weak_duplicate_and_oversized_fields():
    with TestClient(app) as client:
        email = "size.%s@hospital.example" % uuid.uuid4().hex[:8]
        assert (
            _register(client, email=email, first_name="").status_code == 422
        )
        assert (
            _register(client, email=email, password="short").status_code == 422
        )
        assert (
            _register(client, email=email, password="password").status_code == 422
        )
        assert (
            _register(client, email=email, password="12345678").status_code == 422
        )
        assert _register(client, email="not-an-email", password="secret12").status_code == 422
        created = _register(client, email=email)
        assert created.status_code == 200, created.text
        assert "recovery_code" in created.json()
        assert "password_hash" not in created.json()
        assert "recovery_hash" not in created.json()
        assert _register(client, email=email.upper()).status_code == 409
        huge = _register(client, email="huge.%s@hospital.example" % uuid.uuid4().hex[:8], first_name="A" * 81)
        assert huge.status_code == 422
        huge_pw = _register(
            client,
            email="hugepw.%s@hospital.example" % uuid.uuid4().hex[:8],
            password="x" * 129,
        )
        assert huge_pw.status_code == 422


def test_login_accepts_existing_short_demo_password():
    """Login verifies the stored hash. 'demo' is 4 chars and must not hit new-password rules."""
    auth_routes._ATTEMPTS.clear()
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email": "  Maya.Patel@LENS.demo ", "password": "demo"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["hcp_id"] == "hcp_001"
        assert body["email"] == "maya.patel@lens.demo"
        assert body["session_token"]
        assert "password_hash" not in body
        assert "recovery_code" not in body
        headers = {"Authorization": "Bearer " + body["session_token"]}
        profile = client.get("/profile/hcp_001", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["hcp_id"] == "hcp_001"
        for _ in range(12):
            assert (
                client.post(
                    "/auth/login",
                    json={"email": "maya.patel@lens.demo", "password": "wrong"},
                ).status_code
                == 401
            )
        still = client.post(
            "/auth/login",
            json={"email": "maya.patel@lens.demo", "password": "demo"},
        )
        assert still.status_code == 200, still.text
    auth_routes._ATTEMPTS.clear()


def test_login_does_not_enumerate_or_accept_operator_payloads():
    with TestClient(app) as client:
        email = "enum.%s@hospital.example" % uuid.uuid4().hex[:8]
        assert _register(client, email=email).status_code == 200
        missing = client.post("/auth/login", json={"email": "missing.%s@hospital.example" % uuid.uuid4().hex[:8], "password": "secret12"})
        wrong = client.post("/auth/login", json={"email": email, "password": "wrongpass"})
        assert missing.status_code == 401
        assert wrong.status_code == 401
        assert missing.json()["detail"] == wrong.json()["detail"]
        injected = client.post("/auth/login", json={"email": {"$gt": ""}, "password": "secret12"})
        assert injected.status_code == 422
        later = client.post("/auth/login", json={"email": email, "password": "secret12"})
        assert later.status_code == 200
        assert "recovery_code" not in later.json()


def test_login_and_reset_are_rate_limited():
    auth_routes._ATTEMPTS.clear()
    with TestClient(app) as client:
        email = "rate.%s@hospital.example" % uuid.uuid4().hex[:8]
        assert _register(client, email=email).status_code == 200
        for _ in range(8):
            assert client.post("/auth/login", json={"email": email, "password": "wrongpass"}).status_code == 401
        locked = client.post("/auth/login", json={"email": email, "password": "secret12"})
        assert locked.status_code == 429
        ghost = "ghost.%s@hospital.example" % uuid.uuid4().hex[:8]
        for _ in range(8):
            assert client.post(
                "/auth/forgot-password",
                json={"email": ghost, "recovery_code": "WRONGCODE1"},
            ).status_code == 401
        assert (
            client.post(
                "/auth/forgot-password",
                json={"email": ghost, "recovery_code": "WRONGCODE1"},
            ).status_code
            == 429
        )
    auth_routes._ATTEMPTS.clear()


def test_empty_hcp_id_cannot_skip_ownership():
    with TestClient(app) as client:
        headers, body = login(client)
        assert client.get("/profile/", headers=headers).status_code == 404
        assert client.get("/drug/adderall/summary", params={"hcp_id": ""}, headers=headers).status_code == 403
        assert client.post(
            "/drug/adderall/ask",
            json={"hcp_id": "", "query": "dose"},
            headers=headers,
        ).status_code == 403
        assert client.post(
            "/engagement/log",
            json={"hcp_id": "", "drug_id": "adderall"},
            headers=headers,
        ).status_code == 403
        assert client.get("/profile/%s/chats" % body["hcp_id"], headers=headers).status_code == 200


def test_session_cannot_read_or_write_another_account():
    with TestClient(app) as client:
        maya, _ = login(client, "hcp_001")
        created = _register(client, email="other.%s@hospital.example" % uuid.uuid4().hex[:8])
        other_id = created.json()["hcp_id"]
        other = {"Authorization": "Bearer " + created.json()["session_token"]}
        assert client.get("/profile/" + other_id, headers=maya).status_code == 403
        assert client.get("/profile/%s/patients" % other_id, headers=maya).status_code == 403
        assert client.get("/profile/%s/chats" % other_id, headers=maya).status_code == 403
        assert client.patch("/profile/" + other_id, json={"specialty": "Hacked"}, headers=maya).status_code == 403
        assert client.get(
            "/drug/adderall/summary", params={"hcp_id": other_id}, headers=maya
        ).status_code == 403
        assert client.post(
            "/drug/adderall/ask",
            json={"hcp_id": other_id, "query": "dose"},
            headers=maya,
        ).status_code == 403
        assert client.post(
            "/engagement/log",
            json={"hcp_id": other_id, "drug_id": "adderall"},
            headers=maya,
        ).status_code == 403
        assert client.get("/patients/pat_001", headers=other).status_code == 404


def test_reset_rejects_swap_reuse_and_missing_recovery():
    with TestClient(app) as client:
        one = _register(client, email="reset1.%s@hospital.example" % uuid.uuid4().hex[:8]).json()
        two = _register(client, email="reset2.%s@hospital.example" % uuid.uuid4().hex[:8]).json()
        started = client.post(
            "/auth/forgot-password",
            json={"email": one["email"], "recovery_code": one["recovery_code"]},
        )
        assert started.status_code == 200
        token = started.json()["reset_token"]
        swapped = client.post(
            "/auth/reset-password",
            json={"email": two["email"], "reset_token": token, "new_password": "newpass12"},
        )
        assert swapped.status_code == 401
        reused = client.post(
            "/auth/reset-password",
            json={"email": one["email"], "reset_token": token, "new_password": "newpass12"},
        )
        assert reused.status_code == 401
        assert client.post(
            "/auth/login",
            json={"email": one["email"], "password": "secret12"},
        ).status_code == 200
        assert client.post(
            "/auth/forgot-password",
            json={"email": one["email"], "recovery_code": ""},
        ).status_code == 401


def test_logout_and_password_change_revoke_sessions():
    with TestClient(app) as client:
        created = _register(client).json()
        headers = {"Authorization": "Bearer " + created["session_token"]}
        assert client.post("/auth/logout", headers=headers).status_code == 200
        assert client.get("/profile/" + created["hcp_id"], headers=headers).status_code == 401

        again = client.post(
            "/auth/login",
            json={"email": created["email"], "password": "secret12"},
        ).json()
        first = {"Authorization": "Bearer " + again["session_token"]}
        second = client.post(
            "/auth/login",
            json={"email": created["email"], "password": "secret12"},
        ).json()
        other = {"Authorization": "Bearer " + second["session_token"]}
        changed = client.post(
            "/auth/change-password",
            json={"current_password": "secret12", "new_password": "newerpass1"},
            headers=first,
        )
        assert changed.status_code == 200
        assert client.get("/profile/" + created["hcp_id"], headers=first).status_code == 401
        assert client.get("/profile/" + created["hcp_id"], headers=other).status_code == 401
        fresh = {"Authorization": "Bearer " + changed.json()["session_token"]}
        assert client.get("/profile/" + created["hcp_id"], headers=fresh).status_code == 200
        assert client.post(
            "/auth/change-password",
            json={"new_password": "another12"},
            headers=fresh,
        ).status_code == 422
        assert client.post(
            "/auth/change-password",
            json={"current_password": "wrongpass", "new_password": "another12"},
            headers=fresh,
        ).status_code == 401


def test_email_change_requires_password_and_valid_address():
    with TestClient(app) as client:
        created = _register(client).json()
        headers = {"Authorization": "Bearer " + created["session_token"]}
        taken = _register(client).json()["email"]
        assert (
            client.patch(
                "/profile/" + created["hcp_id"],
                json={"email": "not-an-email"},
                headers=headers,
            ).status_code
            == 422
        )
        assert (
            client.patch(
                "/profile/" + created["hcp_id"],
                json={"email": "fresh.%s@hospital.example" % uuid.uuid4().hex[:8]},
                headers=headers,
            ).status_code
            == 401
        )
        assert (
            client.patch(
                "/profile/" + created["hcp_id"],
                json={"email": taken, "current_password": "secret12"},
                headers=headers,
            ).status_code
            == 409
        )
        nxt = "fresh.%s@hospital.example" % uuid.uuid4().hex[:8]
        ok = client.patch(
            "/profile/" + created["hcp_id"],
            json={"email": nxt, "current_password": "secret12"},
            headers=headers,
        )
        assert ok.status_code == 200
        assert ok.json()["email"] == nxt
        assert (
            client.patch(
                "/profile/" + created["hcp_id"],
                json={"first_name": ""},
                headers=headers,
            ).status_code
            == 422
        )


def test_private_routes_require_bearer_token():
    with TestClient(app) as client:
        created = _register(client).json()
        hcp_id = created["hcp_id"]
        assert client.post("/auth/logout").status_code == 401
        assert client.post(
            "/auth/change-password",
            json={"current_password": "secret12", "new_password": "newerpass1"},
        ).status_code == 401
        assert client.get("/profile/" + hcp_id).status_code == 401
        assert client.get("/profile/%s/patients" % hcp_id).status_code == 401
        assert client.get("/profile/%s/chats" % hcp_id).status_code == 401
        assert client.get("/patients/pat_001").status_code == 401
        assert client.post("/patients/sync").status_code == 401
        assert client.get("/patients/pat_001/medication-reviews").status_code == 401
        assert client.get("/drug/adderall/summary", params={"hcp_id": hcp_id}).status_code == 401
        assert client.post("/drug/adderall/ask", json={"hcp_id": hcp_id, "query": "dose"}).status_code == 401
        assert client.post("/engagement/log", json={"hcp_id": hcp_id, "drug_id": "adderall"}).status_code == 401
