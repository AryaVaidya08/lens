from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.medication_access import AccessInput, POLICY, assess
from tests.auth_util import login


def complete():
    return dict(policy_id=POLICY["id"], policy_confirmed=True, medication="rivaroxaban", strength="10 mg",
                formulation="tablet", directions="As documented in prescription", quantity="30 tablets / 30 days",
                indication="Documented indication", payer=POLICY["payer"], plan="QA plan", member_id="TEST-ONLY",
                patient_dob="2000-01-01", prescriber="Test prescriber / NPI", prescriber_contact="Test contact",
                rationale="Patient-specific rationale entered by clinician.", evidence=[dict(
                    requirement_id="brand_exception", text="Documented reason brand cannot be used.",
                    source="Test encounter note, 2026-09-26", confirmed=True)])


def request_body(response):
    return {k: response[k] for k in AccessInput.model_fields}


def test_gaps_do_not_invent_clinical_evidence():
    policy, missing = assess(AccessInput())
    assert policy is None
    assert "Patient-specific clinical rationale" in missing
    payload = complete()
    assert assess(AccessInput(**payload))[1] == []
    payload["evidence"][0]["source"] = " "
    assert any("evidence, source" in s for s in assess(AccessInput(**payload))[1])
    payload["evidence"][0].update(source="a note", confirmed=False)
    assert any("review required" in s for s in assess(AccessInput(**payload))[1])


@pytest.mark.parametrize("field,value", [("medication", "Xarelto"), ("strength", "2.5 mg"),
                                        ("formulation", "suspension"), ("payer", "Different payer")])
def test_policy_scope_is_checked(field, value):
    p = complete()
    p[field] = value
    assert any("does not match" in s for s in assess(AccessInput(**p))[1])


def test_custom_policies_need_source_and_explicit_requirements():
    p = complete()
    p.update(policy_id="custom", evidence=[])
    assert any("Policy title" in s for s in assess(AccessInput(**p))[1])
    p.update(policy_title="Actual payer policy", policy_source="Payer document reference",
             policy_date="2026-09-26", requirements=[dict(id="trial", title="Prior trial", detail="Trial or exception")])
    assert any("Prior trial" in s for s in assess(AccessInput(**p))[1])
    p["evidence"] = [dict(requirement_id="trial", text="Confirmed history", source="Dated note", confirmed=True)]
    assert assess(AccessInput(**p))[1] == []


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(status="autoapproved"),
    lambda p: p.update(revision=-1),
    lambda p: p["evidence"].append(deepcopy(p["evidence"][0])),
    lambda p: p.update(requirements=[dict(id="x", title=" ")]),
    lambda p: p.update(hcp_id="hcp_002"),
])
def test_bad_inputs_rejected(mutation):
    p = complete()
    mutation(p)
    with pytest.raises(ValueError):
        AccessInput(**p)


def test_full_workflow_and_immutable_submission_snapshot():
    with TestClient(app) as c:
        headers, _ = login(c)
        base = "/patients/pat_001/medication-access"
        path = f"{base}/{uuid4()}"
        chart = c.get("/patients/pat_001", headers=headers).json()
        p = complete()
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["revision"] == 1 and body["missing"] == []
        assert "Elena Vasquez" in body["letter"]
        assert body["reviewed"] is False and "signature" in body["letter"]
        assert c.put(path, json=p, headers=headers).status_code == 409
        assert c.get(base, headers=headers).json()["cases"][0] == body
        p = request_body(body)
        p.update(status="ready")
        assert c.put(path, json=p, headers=headers).status_code == 422
        p.update(reviewed=True, letter=body["letter"] + "\nClinician correction.")
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200, r.text
        p = request_body(r.json())
        p.update(status="submitted")
        assert c.put(path, json=p, headers=headers).status_code == 422
        p["status_note"] = "Portal receipt QA-123"
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200, r.text
        snapshot = r.json()["history"][-1]
        assert snapshot["packet"].endswith("Clinician correction.")
        assert snapshot["document"]["evidence"][0]["confirmed"] is True
        p = request_body(r.json())
        p["rationale"] = "Changed after submission"
        assert c.put(path, json=p, headers=headers).status_code == 422
        p = request_body(r.json())
        p.update(status="approved", status_note="Payer letter QA-234")
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200, r.text
        p = request_body(r.json())
        p.update(status="obtained", status_note="Patient confirmed receipt today")
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["history"][2] == snapshot
        assert [e["status"] for e in r.json()["history"]] == ["incomplete", "ready", "submitted", "approved", "obtained"]
        assert c.get("/patients/pat_001", headers=headers).json() == chart


def test_denial_reopen_appeal_retains_original_packet():
    with TestClient(app) as c:
        headers, _ = login(c)
        path = f"/patients/pat_001/medication-access/{uuid4()}"
        p = complete()
        p.update(letter="Reviewed initial request", reviewed=True, status="ready")
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200
        p = request_body(r.json())
        p.update(status="submitted", status_note="Receipt 001")
        r = c.put(path, json=p, headers=headers)
        p = request_body(r.json())
        p.update(status="denied", status_note="Missing supporting record")
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200
        p = request_body(r.json())
        p.update(status="incomplete", request_kind="appeal", letter="", reviewed=False)
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200
        assert "Denial reason" in r.json()["missing"]
        assert "appeal" in r.json()["letter"]
        assert r.json()["history"][1]["packet"] == "Reviewed initial request"
        p = request_body(r.json())
        p.update(denial_reason="Missing supporting record", denial_reference="Notice dated 2026-09-26, ref 002; instructions entered",
                 status="ready", reviewed=True, letter="Reviewed appeal")
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200, r.text


def test_auth_ownership_unknown_policy_and_bad_evidence():
    with TestClient(app) as c:
        owner, _ = login(c)
        other, _ = login(c, "hcp_002")
        base = "/patients/pat_001/medication-access"
        path = f"{base}/{uuid4()}"
        assert c.get("/medication-access/policies").status_code == 401
        assert c.get("/medication-access/policies", headers=owner).json()["policies"] == [POLICY]
        for headers, code in [({}, 401), (other, 404)]:
            assert c.get(base, headers=headers).status_code == code
            assert c.put(path, json=complete(), headers=headers).status_code == code
        p = complete()
        p["policy_id"] = "invented"
        assert c.put(path, json=p, headers=owner).status_code == 422
        p = complete()
        p["evidence"][0]["requirement_id"] = "invented"
        assert c.put(path, json=p, headers=owner).status_code == 422
        p = complete()
        p.update(status="approved", status_note="Attempt to skip submission")
        assert c.put(path, json=p, headers=owner).status_code == 422


def test_missing_data_cannot_be_marked_ready_and_draft_regeneration_is_honest():
    with TestClient(app) as c:
        headers, _ = login(c)
        path = f"/patients/pat_001/medication-access/{uuid4()}"
        r = c.put(path, json={}, headers=headers)
        assert r.status_code == 200
        assert "MISSING" in r.json()["letter"]
        p = request_body(r.json())
        p.update(status="ready", reviewed=True)
        assert c.put(path, json=p, headers=headers).status_code == 422
        p.update(status="incomplete", rationale="New confirmed rationale", letter="", reviewed=True)
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200
        assert "New confirmed rationale" in r.json()["letter"]
        assert r.json()["reviewed"] is False


def test_changed_facts_invalidate_retained_letter_on_backend():
    with TestClient(app) as c:
        headers, _ = login(c)
        path = f"/patients/pat_001/medication-access/{uuid4()}"
        r = c.put(path, json=complete(), headers=headers)
        p = request_body(r.json())
        p.update(reviewed=True, status="ready")
        r = c.put(path, json=p, headers=headers)
        p = request_body(r.json())
        p["rationale"] = "Changed rationale"
        assert c.put(path, json=p, headers=headers).status_code == 422
        p["status"] = "incomplete"
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200
        assert r.json()["reviewed"] is False
        assert "Changed rationale" in r.json()["letter"]


def test_large_valid_evidence_packet_can_be_saved_again():
    with TestClient(app) as c:
        headers, _ = login(c)
        path = f"/patients/pat_001/medication-access/{uuid4()}"
        p = complete()
        p.update(policy_id="custom", policy_title="QA policy", policy_source="QA source", policy_date="QA version",
                 requirements=[dict(id=str(i), title="Requirement " + str(i)) for i in range(30)],
                 evidence=[dict(requirement_id=str(i), text="a" * 6000, source="QA note", confirmed=True) for i in range(30)])
        r = c.put(path, json=p, headers=headers)
        assert r.status_code == 200
        assert len(r.json()["letter"]) > 30000
        p = request_body(r.json())
        p.update(reviewed=True, status="ready")
        assert c.put(path, json=p, headers=headers).status_code == 200
