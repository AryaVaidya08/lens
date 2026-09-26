"""Registered clinicians land in `hcps` and survive seed()."""

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import _apply_env_line, _load_env_file, mongodb_kind
from app.db.mongo import get_database, store_info
from app.db.seed import DEMO_IDS, seed
from app.main import app
from tests.test_auth_hardening import _register


def test_register_inserts_hcps_row_and_survives_seed():
    with TestClient(app) as client:
        email = "persist.%s@hospital.example" % uuid.uuid4().hex[:8]
        created = _register(client, email=email)
        assert created.status_code == 200, created.text
        body = created.json()
        hcp_id = body["hcp_id"]
        assert hcp_id.startswith("hcp_")
        assert hcp_id not in DEMO_IDS
        assert body["email"] == email

        db = get_database()
        assert "users" not in db.list_collection_names()
        row = db.hcps.find_one({"_id": hcp_id})
        assert row is not None
        assert row["email"] == email
        assert row["account_source"] == "register"
        assert row.get("created_at") is not None
        assert row.get("password_hash")

        before = db.hcps.count_documents({})
        seed(db)
        assert db.hcps.find_one({"_id": hcp_id, "email": email}) is not None
        assert db.hcps.count_documents({}) >= before
        assert db.hcps.find_one({"_id": hcp_id})["password_hash"] == row["password_hash"]

        again = client.post("/auth/login", json={"email": email, "password": "secret12"})
        assert again.status_code == 200
        assert again.json()["hcp_id"] == hcp_id


def test_store_info_points_at_hcps_without_leaking_uri():
    info = store_info()
    assert info["accounts_collection"] == "hcps"
    assert info["mongodb_db"]
    assert info["mongodb_kind"] in {"atlas", "localhost", "mongomock", "other"}
    assert "mongodb_uri" not in info
    assert "://" not in str(info.values())


def test_env_loader_reads_home_file_and_keeps_existing(tmp_path):
    environ = {"MONGODB_URI": "mongomock://localhost"}
    path = tmp_path / ".lens-mongodb.env"
    path.write_text(
        'export MONGODB_URI="mongodb+srv://example.mongodb.net/"\n'
        "MONGODB_DB=lens\n"
        "# comment\n"
    )
    _load_env_file(path, environ)
    assert environ["MONGODB_URI"] == "mongomock://localhost"
    assert environ["MONGODB_DB"] == "lens"

    empty = {}
    _apply_env_line("export MONGODB_DB=from_home", empty)
    assert empty["MONGODB_DB"] == "from_home"
    assert mongodb_kind("mongodb+srv://cluster.mongodb.net/") == "atlas"
    assert mongodb_kind("mongodb://127.0.0.1:27017") == "localhost"
    assert mongodb_kind("mongomock://localhost") == "mongomock"
    assert Path.home().joinpath(".lens-mongodb.env").name == ".lens-mongodb.env"
