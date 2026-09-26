import pytest

from app.db.database import init_db
from app.db.seed import seed


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_detect_by_barcode(client):
    resp = client.post("/detect", json={"barcode": "3-00000-00171", "ocr_text": None})
    assert resp.status_code == 200
    body = resp.json()
    assert body["drug_id"] == "ibuprofen"
    assert body["name"] == "Ibuprofen"


def test_detect_by_ocr_fuzzy_match(client):
    resp = client.post("/detect", json={"barcode": None, "ocr_text": "TYLENOL Extra Strength"})
    assert resp.status_code == 200
    assert resp.json()["drug_id"] == "tylenol"


def test_detect_no_match_returns_404(client):
    resp = client.post("/detect", json={"barcode": "0000000000", "ocr_text": "not a real drug at all"})
    assert resp.status_code == 404


def test_detect_ocr_prefers_brand_name_over_generic_when_both_present(client):
    # Real packaging OCR often picks up both the brand and the generic name.
    # The brand printed first/largest on the box should win, not whichever
    # row the DB happens to return first for a tied fuzzy score.
    resp = client.post("/detect", json={"barcode": None, "ocr_text": "ADVIL Ibuprofen Tablets 200mg"})
    assert resp.status_code == 200
    assert resp.json()["drug_id"] == "advil"


def test_detect_ocr_short_fragment_does_not_false_match(client):
    resp = client.post("/detect", json={"barcode": None, "ocr_text": "a"})
    assert resp.status_code == 404


def test_detect_ocr_similar_but_wrong_name_does_not_match(client):
    resp = client.post("/detect", json={"barcode": None, "ocr_text": "Abilify"})
    assert resp.status_code == 404
