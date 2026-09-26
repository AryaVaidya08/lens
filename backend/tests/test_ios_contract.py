"""
Hostile cases for the iOS ↔ backend contract.

Bodies are the JSON Foundation's JSONEncoder actually emits: null for a
missing optional, snake_case keys from the CodingKeys in APIClient.swift.
"""

from fastapi.testclient import TestClient

from app.main import app
from tests.auth_util import login

# Exact payloads the iOS client sends (see Lens/Tests/ContractChecks.swift).
IOS_DETECT_OCR = {"barcode": None, "ocr_text": "LORAZEPAM 1 mg tablets"}
IOS_DETECT_BARCODE = {"barcode": "0363323012345", "ocr_text": None}
IOS_ASK = {"hcp_id": "hcp_001", "query": "how should I dose this"}
IOS_ENGAGEMENT = {"hcp_id": "hcp_001", "drug_id": "biofreeze"}


def test_ios_detect_sends_null_for_unused_field():
    with TestClient(app) as client:
        ocr = client.post("/detect", json=IOS_DETECT_OCR)
        assert ocr.status_code == 200
        assert ocr.json() == {"drug_id": "lorazepam", "name": "Lorazepam"}

        barcode = client.post("/detect", json=IOS_DETECT_BARCODE)
        assert barcode.json()["drug_id"] == "adderall"


def test_ios_ask_and_engagement_bodies():
    with TestClient(app) as client:
        headers, _ = login(client)
        ask = client.post("/drug/adderall/ask", json=IOS_ASK, headers=headers)
        assert ask.status_code == 200
        assert "answer_text" in ask.json()
        assert ask.json()["answer_text"]
        log = client.post("/engagement/log", json=IOS_ENGAGEMENT, headers=headers)
        assert log.status_code == 200
        assert isinstance(log.json()["touch_count"], int)


def test_ios_summary_query_item():
    with TestClient(app) as client:
        headers, _ = login(client)
        response = client.get(
            "/drug/biofreeze/summary", params={"hcp_id": "hcp_001"}, headers=headers
        )
        body = response.json()
        assert response.status_code == 200
        assert set(body) == {"drug_id", "name", "tier", "headline", "bullets"}
        assert body["tier"] in {"new", "returning", "expert"}
        assert isinstance(body["bullets"], list)


def test_trailing_slash_does_not_eat_post_body():
    with TestClient(app) as client:
        redirected = client.post("/detect/", json=IOS_DETECT_OCR)
        # 404 (no redirect) is safe. 307/308 would drop the POST body on follow.
        assert redirected.status_code == 404
        assert client.post("/detect", json=IOS_DETECT_OCR).status_code == 200


def test_empty_and_whitespace_payloads():
    with TestClient(app) as client:
        assert client.post("/detect", json={}).status_code == 404
        assert client.post("/detect", json={"barcode": None, "ocr_text": None}).status_code == 404
        assert client.post("/detect", json={"barcode": "   ", "ocr_text": ""}).status_code == 404
        headers, _ = login(client)
        assert client.post(
            "/drug/adderall/ask", json={"hcp_id": "hcp_001", "query": "   "}, headers=headers
        ).status_code == 422
        assert client.post(
            "/drug/adderall/ask", json={"hcp_id": "hcp_001", "query": ""}, headers=headers
        ).status_code == 422


def test_unknown_ids_are_404_not_500():
    with TestClient(app) as client:
        headers, _ = login(client)
        assert client.get("/profile/hcp_999", headers=headers).status_code == 403
        assert client.get(
            "/drug/not-a-drug/summary", params={"hcp_id": "hcp_001"}, headers=headers
        ).status_code == 404
        assert client.post("/drug/not-a-drug/ask", json=IOS_ASK, headers=headers).status_code == 404
        assert client.post(
            "/engagement/log", json={"hcp_id": "hcp_999", "drug_id": "adderall"}, headers=headers
        ).status_code == 403
        assert client.post(
            "/engagement/log", json={"hcp_id": "hcp_001", "drug_id": "not-a-drug"}, headers=headers
        ).status_code == 404


def test_unknown_hcp_id_cannot_spoof_another_account():
    with TestClient(app) as client:
        headers, _ = login(client)
        assert client.get(
            "/drug/adderall/summary", params={"hcp_id": "hcp_999"}, headers=headers
        ).status_code == 403
        body = client.get(
            "/drug/adderall/summary", params={"hcp_id": "hcp_001"}, headers=headers
        ).json()
        assert body["tier"] in {"new", "returning", "expert"}
        assert body["bullets"]


def test_formatted_and_noisy_barcodes():
    with TestClient(app) as client:
        dashed = client.post("/detect", json={"barcode": "0363-3230-12345", "ocr_text": None})
        assert dashed.json()["drug_id"] == "adderall"
        spaced = client.post("/detect", json={"barcode": " 0363323012345 ", "ocr_text": None})
        assert spaced.json()["drug_id"] == "adderall"
        gs1 = client.post("/detect", json={"barcode": "010363323012345", "ocr_text": None})
        # Extra digits must not silently match a different bottle.
        assert gs1.status_code == 404


def test_ocr_noise_newlines_unicode_and_alias():
    with TestClient(app) as client:
        noisy = client.post(
            "/detect",
            json={"barcode": None, "ocr_text": "NDC 00543\nAtivan® 1 mg\nLot A12"},
        )
        assert noisy.json()["drug_id"] == "lorazepam"
        long_text = "lorem " * 400 + " BIOFREEZE " + "ipsum " * 400
        assert client.post("/detect", json={"ocr_text": long_text}).json()["drug_id"] == "biofreeze"


def test_wrong_barcode_falls_back_to_ocr():
    with TestClient(app) as client:
        body = client.post(
            "/detect",
            json={"barcode": "0000000000000", "ocr_text": "Adderall XR 20 mg"},
        )
        assert body.json()["drug_id"] == "adderall"


def test_extra_fields_from_a_newer_app_are_ignored():
    with TestClient(app) as client:
        body = client.post(
            "/detect",
            json={"barcode": None, "ocr_text": "lorazepam", "kind": "text", "confidence": 0.9},
        )
        assert body.status_code == 200
        headers, _ = login(client)
        ask = client.post(
            "/drug/lorazepam/ask",
            json={"hcp_id": "hcp_001", "query": "side effects", "locale": "en-US"},
            headers=headers,
        )
        assert ask.status_code == 200


def test_missing_required_ask_fields():
    with TestClient(app) as client:
        headers, _ = login(client)
        assert client.post("/drug/adderall/ask", json={"query": "dose"}, headers=headers).status_code == 422
        assert client.post("/drug/adderall/ask", json={"hcp_id": "hcp_001"}, headers=headers).status_code == 422
        assert client.get("/drug/adderall/summary").status_code == 401
        assert client.get("/drug/adderall/summary", headers=headers).status_code == 422


def test_profile_shape_matches_hcp_swift():
    with TestClient(app) as client:
        headers, _ = login(client)
        body = client.get("/profile/hcp_001", headers=headers).json()
        assert set(body.keys()) >= {"hcp_id", "name", "specialty", "familiarity"}
        assert "id" not in body
        assert isinstance(body["familiarity"], dict)


def test_detect_response_uses_drug_id_not_id():
    with TestClient(app) as client:
        body = client.post("/detect", json=IOS_DETECT_BARCODE).json()
        assert "id" not in body
        assert body["drug_id"] == "adderall"
