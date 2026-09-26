"""Broad regression cases for detect, chart flags, and authz."""

import pytest

from app.personalization.patient_check import check_patient_chart
from tests.auth_util import login

DETECT_HITS = [
    ("ocr", "Adderall", "adderall"),
    ("ocr", "ADDERALL 10 mg", "adderall"),
    ("ocr", "Adderall XR 20 mg", "adderall"),
    ("ocr", "Lorazepam", "lorazepam"),
    ("ocr", "LORAZEPAM 1 mg", "lorazepam"),
    ("ocr", "LORAZEPAM 1 mg tablets", "lorazepam"),
    ("ocr", "Ativan 1mg", "lorazepam"),
    ("ocr", "Ativan® 1 mg", "lorazepam"),
    ("ocr", "Biofreeze", "biofreeze"),
    ("ocr", "BIOFREEZE", "biofreeze"),
    ("ocr", "Biofreeze gel", "biofreeze"),
    ("barcode", "0363323012345", "adderall"),
    ("barcode", "0363-3230-12345", "adderall"),
    ("barcode", " 0363323012345 ", "adderall"),
    ("barcode", "0357844110014", "adderall"),
    ("barcode", "0362135861018", "lorazepam"),
    ("barcode", "0731124100009", "biofreeze"),
    ("ocr", " ibuprofen ", "ibuprofen"),
    ("ocr", "TYLENOL", "tylenol"),
    ("ocr", "Advil Ibuprofen", "advil"),
]

DETECT_MISSES = [
    ("ocr", "unrelated carton"),
    ("ocr", "unrelated carton 99"),
    ("ocr", "a"),
    ("ocr", "   "),
    ("ocr", "zzzzzzq nomatch"),
    ("ocr", "qxv9-not-a-label"),
    ("barcode", "0000000000000"),
    ("barcode", "0000000000"),
    ("barcode", "9999999999999"),
    ("barcode", "010363323012345"),
    ("barcode", "1111111111111"),
    ("barcode", "abc"),
    ("ocr", "????"),
    ("ocr", "12345 only"),
    ("ocr", "no such product xyz"),
    ("barcode", "not-a-upc"),
]

CHART_FLAGS = [
    (
        "pat_a",
        "Elena",
        "Vasquez",
        "Penicillin, amphetamines",
        "Metformin 1000 mg BID",
        "adderall",
        "Adderall",
        "flag",
    ),
    (
        "pat_b",
        "Marcus",
        "Hale",
        "None known",
        "None",
        "adderall",
        "Adderall",
        "clear",
    ),
    (
        "pat_c",
        "Priya",
        "Shah",
        "Sulfa",
        "Apixaban, metoprolol",
        "biofreeze",
        "Biofreeze",
        "clear",
    ),
    (
        "pat_d",
        "Owen",
        "Blake",
        "Latex",
        "Insulin aspart",
        "lorazepam",
        "Lorazepam",
        "clear",
    ),
    (
        "pat_e",
        "Nina",
        "Cole",
        "lorazepam",
        "None",
        "lorazepam",
        "Lorazepam",
        "flag",
    ),
    (
        "pat_f",
        "Sam",
        "Lee",
        "NKA",
        "Adderall 10 mg",
        "adderall",
        "Adderall",
        "flag",
    ),
    (
        "pat_g",
        "Ava",
        "Ng",
        "nkda",
        "none",
        "biofreeze",
        "Biofreeze",
        "clear",
    ),
    (
        "pat_h",
        "Jon",
        "Park",
        "amphetamine",
        "",
        "adderall",
        "Adderall",
        "flag",
    ),
    (
        "pat_i",
        "Lia",
        "Ortiz",
        "Penicillin",
        "Metformin",
        "biofreeze",
        "Biofreeze",
        "clear",
    ),
    (
        "pat_j",
        "Max",
        "Cho",
        "ativan",
        "None",
        "lorazepam",
        "Lorazepam",
        "flag",
    ),
]

PRIVATE_GETS = [
    "/profile/hcp_001",
    "/profile/hcp_001/patients",
    "/patients/pat_001",
    "/patients/pat_001/medication-reviews",
    "/drug/adderall/summary?hcp_id=hcp_001",
]


def test_detect_hits(client):
    for kind, payload, drug_id in DETECT_HITS:
        body = {"barcode": payload, "ocr_text": None} if kind == "barcode" else {
            "barcode": None,
            "ocr_text": payload,
        }
        response = client.post("/detect", json=body)
        assert response.status_code == 200, (payload, response.text)
        assert response.json()["drug_id"] == drug_id


def test_detect_misses(client):
    for kind, payload in DETECT_MISSES:
        body = {"barcode": payload, "ocr_text": None} if kind == "barcode" else {
            "barcode": None,
            "ocr_text": payload,
        }
        assert client.post("/detect", json=body).status_code == 404, payload


@pytest.mark.parametrize("kind,payload,drug_id", DETECT_HITS)
def test_each_detect_hit(client, kind, payload, drug_id):
    body = {"barcode": payload, "ocr_text": None} if kind == "barcode" else {
        "barcode": None,
        "ocr_text": payload,
    }
    response = client.post("/detect", json=body)
    assert response.status_code == 200
    assert response.json()["drug_id"] == drug_id
    assert response.json()["name"]


@pytest.mark.parametrize("kind,payload", DETECT_MISSES)
def test_each_detect_miss(client, kind, payload):
    body = {"barcode": payload, "ocr_text": None} if kind == "barcode" else {
        "barcode": None,
        "ocr_text": payload,
    }
    assert client.post("/detect", json=body).status_code == 404


@pytest.mark.parametrize(
    "pid,first,last,allergies,meds,drug_id,drug_name,status",
    CHART_FLAGS,
)
def test_each_chart_flag(pid, first, last, allergies, meds, drug_id, drug_name, status):
    check = check_patient_chart(
        {
            "_id": pid,
            "first_name": first,
            "last_name": last,
            "allergies": allergies,
            "current_medications": meds,
        },
        drug_id,
        drug_name,
    )
    assert check["status"] == status
    assert check["patient_id"] == pid
    assert check["disclaimer"]
    if status == "flag":
        assert check["flags"]
    else:
        assert check["flags"] == []


@pytest.mark.parametrize("path", PRIVATE_GETS)
def test_each_private_get_requires_auth(client, path):
    assert client.get(path).status_code in {401, 403, 422}


@pytest.mark.parametrize("other", ["pat_003", "pat_004", "pat_999", "pat_000", "nope"])
def test_maya_cannot_check_foreign_or_missing_patients(client, other):
    headers, _ = login(client, "hcp_001")
    assert (
        client.get(
            "/drug/adderall/summary",
            params={"hcp_id": "hcp_001", "patient_id": other},
            headers=headers,
        ).status_code
        == 404
    )


@pytest.mark.parametrize("empty", ["", "   "])
def test_blank_patient_id_is_no_check(client, empty):
    headers, _ = login(client, "hcp_001")
    body = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": "hcp_001", "patient_id": empty},
        headers=headers,
    ).json()
    assert body["patient_check"] is None


@pytest.mark.parametrize("drug_id", ["adderall", "lorazepam", "biofreeze", "ibuprofen", "tylenol"])
def test_summary_shape_for_demo_drugs(client, drug_id):
    headers, _ = login(client, "hcp_001")
    body = client.get(
        "/drug/%s/summary" % drug_id,
        params={"hcp_id": "hcp_001"},
        headers=headers,
    ).json()
    assert set(body) == {
        "drug_id",
        "name",
        "tier",
        "headline",
        "bullets",
        "patient_check",
        "full_bullets",
    }
    assert body["tier"] in {"new", "returning", "expert"}
    assert isinstance(body["bullets"], list)
    assert body["patient_check"] is None


@pytest.mark.parametrize("path_id", ["../adderall", "..", "null", "../../../etc/passwd"])
def test_pathlike_drug_ids_404(client, path_id):
    headers, _ = login(client, "hcp_001")
    assert (
        client.get(
            "/drug/%s/summary" % path_id,
            params={"hcp_id": "hcp_001"},
            headers=headers,
        ).status_code
        == 404
    )


@pytest.mark.parametrize("hcp_id", ["hcp_002", "hcp_003", "hcp_999", "hcp_000"])
def test_cannot_log_engagement_as_someone_else(client, hcp_id):
    headers, _ = login(client, "hcp_001")
    assert (
        client.post(
            "/engagement/log",
            json={"hcp_id": hcp_id, "drug_id": "adderall"},
            headers=headers,
        ).status_code
        == 403
    )


@pytest.mark.parametrize("email,password", [
    ("nobody@lens.demo", "demo"),
    ("missing.one@lens.demo", "nope"),
    ("missing.two@lens.demo", "password"),
    ("missing.three@lens.demo", "1234"),
    ("missing.four@lens.demo", "demo"),
])
def test_login_failures_look_the_same(client, email, password):
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower() or "email" in response.json()["detail"].lower()


@pytest.mark.parametrize("first,last", [
    ("Ana", "Diaz"),
    ("Bo", "Kim"),
    ("Chris", "O'Neill"),
    ("Dee", "Wu"),
    ("Eli", "Cruz"),
    ("Fay", "Singh"),
    ("Gus", "Bell"),
    ("Hana", "Ito"),
    ("Ivy", "Moss"),
    ("Jed", "Poe"),
    ("Kai", "Rao"),
    ("Liv", "Sun"),
    ("Mo", "Tan"),
    ("Nia", "Voss"),
])
def test_clear_chart_stays_clear_for_biofreeze(first, last):
    check = check_patient_chart(
        {
            "_id": "pat_x",
            "first_name": first,
            "last_name": last,
            "allergies": "None known",
            "current_medications": "None",
        },
        "biofreeze",
        "Biofreeze",
    )
    assert check["status"] == "clear"
