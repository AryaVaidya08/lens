from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.medication_reviews import ReviewInput, compare
from tests.auth_util import login


def medication(entry_id="ref1", **overrides):
    return dict(id=entry_id, name="Example medication", strength="5 mg", formulation="tablet",
                directions="Take one daily", **overrides)


def review():
    return dict(reference_source="Discharge list dated Sep 27", reference_verified=True,
                collection_complete=True, reviewed=True, reference=[medication()],
                observed=[medication("bottle1", reported_use="taking")])


def findings(payload):
    return compare(ReviewInput(**payload))


def test_exact_match_case_and_spacing_are_not_discrepancies():
    payload = review()
    payload["observed"][0]["name"] = "  EXAMPLE   medication "
    assert findings(payload) == []


def test_strength_directions_and_actual_use_are_separate_evidence():
    payload = review()
    payload["observed"][0].update(strength="10 mg", directions="Take two daily", reported_use="not_taking", notes="Stopped last week")
    result = findings(payload)
    assert [f["title"] for f in result] == ["Strength text differs", "Directions text differs", "Patient reports not taking"]
    assert "reference: 5 mg; bottle: 10 mg" in result[0]["detail"]
    assert "Stopped last week" in result[2]["detail"]


def test_missing_bottle_does_not_imply_nonadherence():
    payload = review()
    payload["observed"] = []
    result = findings(payload)
    assert len(result) == 1
    assert result[0]["kind"] == "not_located"
    assert "does not establish" in result[0]["detail"]


def test_brand_generic_identity_requires_confirmed_link():
    payload = review()
    payload["observed"][0]["name"] = "Example brand"
    assert {f["kind"] for f in findings(payload)} == {"unmatched", "not_located"}
    payload["observed"][0]["reference_id"] = "ref1"
    assert findings(payload) == []


def test_duplicate_names_are_ambiguous_and_multiple_bottles_are_flagged():
    payload = review()
    payload["reference"].append(medication("ref2"))
    assert "identity" in {f["kind"] for f in findings(payload)}
    payload["reference"].pop()
    payload["observed"].append(medication("bottle2", reported_use="taking"))
    assert [f["kind"] for f in findings(payload)] == ["multiple_bottles"]


def test_unknown_values_never_pass_as_verified_equivalents():
    payload = review()
    payload["reference"][0]["strength"] = ""
    payload["observed"][0].update(strength="", reported_use="unsure")
    assert {f["kind"] for f in findings(payload)} == {"incomplete", "reported_use"}


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(reference_verified=False),
    lambda p: p.update(collection_complete=False),
    lambda p: p.update(reference_source="  "),
    lambda p: p["reference"][0].update(name="  "),
    lambda p: p["observed"][0].update(reference_id="deleted-entry"),
    lambda p: p["observed"].append(deepcopy(p["observed"][0])),
    lambda p: p["observed"][0].update(reported_use="safe"),
])
def test_invalid_reviews_rejected(mutation):
    payload = review()
    mutation(payload)
    with pytest.raises(ValueError):
        ReviewInput(**payload)


def test_save_reopen_compare_conflict_and_chart_unchanged():
    with TestClient(app) as client:
        headers, _ = login(client)
        path = "/patients/pat_001/medication-reviews"
        before = client.get("/patients/pat_001", headers=headers).json()
        review_id = str(uuid4())
        payload = review()
        payload.update(reviewed=False, reference_verified=False)
        saved = client.put(f"{path}/{review_id}", json=payload, headers=headers)
        assert saved.status_code == 200, saved.text
        draft = saved.json()
        assert draft["revision"] == 1 and draft["report"] == "" and draft["findings"] == []
        assert client.get(path, headers=headers).json()["reviews"][0] == draft
        assert client.put(f"{path}/{review_id}", json=payload, headers=headers).status_code == 409
        payload.update(revision=1, reviewed=True, reference_verified=True)
        payload["observed"][0].update(strength="10 mg", notes="Patient says taking as labeled")
        result = client.put(f"{path}/{review_id}", json=payload, headers=headers)
        assert result.status_code == 200
        result = result.json()
        assert result["revision"] == 2
        assert result["findings"][0]["title"] == "Strength text differs"
        assert "Elena Vasquez" in result["report"] and "Patient says taking as labeled" in result["report"]
        assert "Discharge list dated Sep 27" in result["report"]
        assert client.put(f"{path}/{review_id}", json=payload, headers=headers).status_code == 409
        assert client.get("/patients/pat_001", headers=headers).json() == before
        # Editing a compared review as a draft removes the stale report.
        payload.update(revision=2, reviewed=False)
        result = client.put(f"{path}/{review_id}", json=payload, headers=headers).json()
        assert result["report"] == "" and result["findings"] == []


def test_reviews_require_auth_and_patient_ownership_for_reads_and_writes():
    with TestClient(app) as client:
        owner, _ = login(client)
        other, _ = login(client, "hcp_002")
        path = "/patients/pat_001/medication-reviews"
        url = f"{path}/{uuid4()}"
        assert client.put(url, json=review(), headers=owner).status_code == 200
        assert client.get(path).status_code == 401
        assert client.put(url, json=review()).status_code == 401
        assert client.get(path, headers=other).status_code == 404
        assert client.put(url, json=review(), headers=other).status_code == 404
        assert client.get("/patients/pat_002/medication-reviews", headers=owner).json() == {"reviews": []}


def test_empty_list_requires_explicit_confirmations_and_no_safety_claim():
    payload = review()
    payload.update(reference=[], observed=[])
    assert findings(payload) == []
    with TestClient(app) as client:
        headers, _ = login(client)
        response = client.put(f"/patients/pat_001/medication-reviews/{uuid4()}", json=payload, headers=headers)
        assert response.status_code == 200
        assert "not a clinical safety assessment" in response.json()["report"]
