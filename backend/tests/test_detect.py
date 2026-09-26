import pytest
from fastapi.testclient import TestClient

from app.db.database import init_db
from app.db.seed import seed
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_detect_by_barcode():
    resp = client.post("/detect", json={"barcode": "3-00000-00171", "ocr_text": None})
    assert resp.status_code == 200
    body = resp.json()
    assert body["drug_id"] == "ibuprofen"
    assert body["name"] == "Ibuprofen"


def test_detect_by_ocr_fuzzy_match():
    resp = client.post("/detect", json={"barcode": None, "ocr_text": "TYLENOL Extra Strength"})
    assert resp.status_code == 200
    assert resp.json()["drug_id"] == "tylenol"


def test_detect_no_match_returns_404():
    resp = client.post("/detect", json={"barcode": "0000000000", "ocr_text": "not a real drug at all"})
    assert resp.status_code == 404
