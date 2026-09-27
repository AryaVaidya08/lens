def test_detect_by_barcode(client):
    resp = client.post("/detect", json={"barcode": "0363323012345", "ocr_text": None})
    assert resp.status_code == 200
    body = resp.json()
    assert body["drug_id"] == "adderall"
    assert body["name"] == "Adderall"


def test_detect_by_ocr_fuzzy_match(client):
    resp = client.post("/detect", json={"barcode": None, "ocr_text": "TYLENOL Extra Strength"})
    assert resp.status_code == 200
    assert resp.json()["drug_id"] == "tylenol"


def test_detect_no_match_returns_404(client):
    resp = client.post("/detect", json={"barcode": "0000000000", "ocr_text": "qxv9-not-a-label"})
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
    resp = client.post("/detect", json={"barcode": None, "ocr_text": "qxv9-not-a-label"})
    assert resp.status_code == 404


def test_detect_ocr_common_english_does_not_match_a_drug_named_real(client):
    assert client.post("/detect", json={"ocr_text": "not a real drug at all"}).status_code == 404


def test_detect_ativan_alias_resolves_to_lorazepam(client):
    resp = client.post("/detect", json={"ocr_text": "Ativan 1mg"})
    assert resp.status_code == 200
    assert resp.json()["drug_id"] == "lorazepam"


def test_detect_barcode_wins_and_skips_ocr(client):
    resp = client.post(
        "/detect",
        json={"barcode": "0363323012345", "ocr_text": "Lorazepam 1 mg tablets"},
    )
    assert resp.status_code == 200
    assert resp.json()["drug_id"] == "adderall"


def test_detect_catalog_is_loaded(client):
    from app.detection.catalog import size

    status = client.get("/status").json()
    assert status["detect_catalog"] >= 3
    assert size() == status["detect_catalog"]
