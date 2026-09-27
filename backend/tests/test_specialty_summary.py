import re
from pathlib import Path

import pytest

from app.personalization import scorer
from tests.auth_util import login
from tests.test_auth_hardening import _register

_IOS_SPECIALTIES_PATH = (
    Path(__file__).resolve().parents[2] / "Lens" / "Lens" / "Views" / "HealthcareSpecialties.swift"
)


def _ios_picker_specialties() -> list[str]:
    text = _IOS_SPECIALTIES_PATH.read_text(encoding="utf-8")
    labels: list[str] = []
    for block in re.findall(r"specialties:\s*\[(.*?)\]", text, re.S):
        labels.extend(re.findall(r'"([^"]+)"', block))
    return labels


@pytest.fixture
def fields(monkeypatch):
    data = {
        "boxed_warning": "Source safety warning",
        "indications_and_usage": "Source indications",
        "dosage_and_administration": "Source dosing",
        "patient_counseling_information": "Source counseling",
        "drug_interactions": "Source interactions",
        "clinical_pharmacology": "Source pharmacology",
        "pediatric_use": "Source pediatric information",
        "geriatric_use": "Source geriatric information",
        "pregnancy": "Source pregnancy information",
        "drug_abuse_and_dependence": "Source dependence information",
        "renal_impairment": "Source renal information",
        "clinical_studies": "Source studies",
        "adverse_reactions": "Source adverse reactions",
        "warnings_and_cautions": "Source cautions",
        "contraindications": "Source contraindications",
        "warnings": "Source warnings",
    }
    monkeypatch.setattr(scorer, "parse_dossier_fields", lambda _: data)
    return data


@pytest.mark.parametrize("specialty", list(scorer._SPECIALTY_FIELDS))
@pytest.mark.parametrize("tier", scorer.TIERS)
def test_specialty_uses_source_text_and_keeps_safety(fields, specialty, tier):
    headline, bullets = scorer.build_summary_content("test", tier, specialty)
    assert headline == f"{specialty} · {scorer._TIER_HEADLINES[tier]}"
    lead = next(fields[key] for key in scorer._TIER_FIELD_PRIORITY[tier] if fields.get(key))
    assert bullets[0] == lead
    assert fields["boxed_warning"] in bullets
    assert 1 <= len(bullets) <= 3
    assert len(bullets) == len(set(bullets))
    assert all(bullet in fields.values() for bullet in bullets)


def test_same_tier_differs_by_specialty(fields):
    cardio = scorer.build_summary_content("test", "new", "Cardiology")
    endocrine = scorer.build_summary_content("test", "new", "Endocrinology")
    assert cardio[1] != endocrine[1]
    assert fields["indications_and_usage"] in cardio[1]
    assert fields["indications_and_usage"] in endocrine[1]


def test_alias_and_case_normalization(fields):
    family = scorer.build_summary_content("test", "new", "  FAMILY  medicine ")
    primary = scorer.build_summary_content("test", "new", "Primary Care")
    assert family[1] == primary[1]
    assert "FAMILY medicine" in family[0]
    assert "Primary Care" in primary[0]


def test_missing_specialty_stays_generic(fields):
    general = scorer.build_summary_content("test", "new")
    assert scorer.build_summary_content("test", "new", "") == general
    assert scorer.build_summary_content("test", "new", None) == general


def test_any_stored_specialty_keeps_its_label(fields):
    for specialty in ("Other / not listed", "Wilderness Medicine", "Emergency Medicine"):
        headline, bullets = scorer.build_summary_content("test", "new", specialty)
        assert specialty in headline
        assert bullets != scorer.build_summary_content("test", "new")[1]


def test_missing_relevant_section_keeps_specialty_label(monkeypatch):
    monkeypatch.setattr(scorer, "parse_dossier_fields", lambda _: {"indications_and_usage": "Source indications"})
    general = scorer.build_summary_content("test", "new")
    pediatric = scorer.build_summary_content("test", "new", "Pediatrics")
    assert pediatric[1] == general[1]
    assert "Pediatrics" in pediatric[0]


def test_otc_style_label_still_shows_specialty(monkeypatch):
    monkeypatch.setattr(
        scorer,
        "parse_dossier_fields",
        lambda _: {
            "purpose": "Source purpose",
            "indications_and_usage": "Source indications",
            "warnings": "Source warnings",
            "dosage_and_administration": "Source dosing",
        },
    )
    cardio = scorer.build_summary_content("test", "new", "Cardiology")
    neuro = scorer.build_summary_content("test", "new", "Neurology")
    assert "Cardiology" in cardio[0]
    assert "Neurology" in neuro[0]
    assert cardio[0] != neuro[0]
    assert "Source warnings" in cardio[1]


def test_familiarity_still_changes_content(fields):
    rows = [scorer.build_summary_content("test", tier, "Cardiology") for tier in scorer.TIERS]
    assert len({row[0] for row in rows}) == 3
    assert len({tuple(row[1]) for row in rows}) == 3
    assert len({row[1][0] for row in rows}) == 3


def test_route_uses_authenticated_specialty_for_scans(client, monkeypatch):
    from app.routes import drug
    seen = []
    def summary(drug_id, tier, specialty=None, compact=True):
        seen.append(specialty)
        return "Test summary", ["Source text"]
    monkeypatch.setattr(drug, "build_summary_content", summary)
    headers, profile = login(client, "hcp_001")
    result = client.get("/drug/adderall/summary", params={"hcp_id": "hcp_001"}, headers=headers)
    assert result.status_code == 200
    assert seen[-1] == profile["specialty"]
    client.get("/drug/adderall/summary", params={"hcp_id": "hcp_001", "patient_id": "missing"}, headers=headers)
    assert seen[-1] == profile["specialty"]


def test_full_summary_preserves_text_omitted_from_preview(monkeypatch):
    text = "Full source passage " * 60
    monkeypatch.setattr(scorer, "parse_dossier_fields", lambda _: {"indications_and_usage": text})
    assert scorer.build_summary_content("test", "new", compact=False)[1] == [text]
    assert scorer.build_summary_content("test", "new", compact=True)[1] == [text]


def test_ios_picker_and_custom_text_all_resolve(fields):
    labels = _ios_picker_specialties()
    assert len(labels) >= 80
    for label in labels:
        resolved = scorer.resolve_specialty(label)
        assert resolved is not None
        assert resolved[0] == label
        assert resolved[1]
        headline, _ = scorer.build_summary_content("test", "new", label)
        assert label in headline
    other = scorer.resolve_specialty("Other / not listed")
    assert other is not None
    assert other[1] == scorer._SPECIALTY_FIELDS["primary care"]
    custom = scorer.resolve_specialty("Sports Cardiology")
    assert custom is not None
    assert custom[1] == scorer.resolve_specialty("Cardiology")[1]
    assert "Sports Cardiology" in scorer.build_summary_content("test", "new", "Sports Cardiology")[0]


def _auth_headers(body: dict) -> dict:
    return {"Authorization": "Bearer " + body["session_token"]}


def test_registered_users_specialty_shapes_summary_and_ask(client, monkeypatch):
    peds = _register(client, specialty="Pediatrics").json()
    emergency = _register(client, specialty="Emergency Medicine").json()
    assert peds["hcp_id"] != emergency["hcp_id"]
    assert not peds["hcp_id"].endswith("001")

    peds_sum = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": peds["hcp_id"]},
        headers=_auth_headers(peds),
    )
    em_sum = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": emergency["hcp_id"]},
        headers=_auth_headers(emergency),
    )
    assert peds_sum.status_code == 200, peds_sum.text
    assert em_sum.status_code == 200, em_sum.text
    assert "Pediatrics" in peds_sum.json()["headline"]
    assert "Emergency Medicine" in em_sum.json()["headline"]
    assert peds_sum.json()["headline"] != em_sum.json()["headline"]

    seen = []

    def fake_answer(query, context, tier="new", specialty=None, patient_context=None):
        seen.append(specialty)
        return "Answer for %s" % specialty

    from app.routes import drug as drug_route

    monkeypatch.setattr(
        drug_route,
        "retrieve",
        lambda drug_id, query, specialty=None: ["Dosing 5 mg. Interactions with stimulants."],
    )
    monkeypatch.setattr(drug_route, "generate_answer", fake_answer)
    assert (
        client.post(
            "/drug/adderall/ask",
            json={"hcp_id": peds["hcp_id"], "query": "how should I dose this"},
            headers=_auth_headers(peds),
        ).json()["answer_text"]
        == "Answer for Pediatrics"
    )
    assert (
        client.post(
            "/drug/adderall/ask",
            json={"hcp_id": emergency["hcp_id"], "query": "how should I dose this"},
            headers=_auth_headers(emergency),
        ).json()["answer_text"]
        == "Answer for Emergency Medicine"
    )
    assert seen == ["Pediatrics", "Emergency Medicine"]


def test_editing_registered_specialty_changes_summary(client):
    created = _register(client, specialty="Neurology").json()
    headers = _auth_headers(created)
    first = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": created["hcp_id"]},
        headers=headers,
    ).json()
    assert "Neurology" in first["headline"]

    patched = client.patch(
        "/profile/" + created["hcp_id"],
        json={
            "first_name": created["first_name"],
            "last_name": created["last_name"],
            "email": created["email"],
            "professional_role": created["professional_role"],
            "specialty": "Clinical Pharmacy",
        },
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["specialty"] == "Clinical Pharmacy"

    second = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": created["hcp_id"]},
        headers=headers,
    ).json()
    assert "Clinical Pharmacy" in second["headline"]
    assert "Neurology" not in second["headline"]
