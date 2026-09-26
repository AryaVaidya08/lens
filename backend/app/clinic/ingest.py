"""
Load and normalize patient charts from a clinic or hospital source.

Two inputs, same parsed shape:
  - Local JSON files in data/clinic_records/ (hackathon stand-in)
  - CLINIC_API_URL, a hospital/EHR export or FHIR Bundle

Callers must go through ingest.load_clinic_records() so swapping the
source never touches routes or iOS.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.config import settings


def load_clinic_records(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return normalized patient dicts ready to upsert into Mongo."""
    if settings.clinic_api_url:
        raw_rows = _fetch_remote(settings.clinic_api_url)
    else:
        raw_rows = _load_local(Path(path or settings.clinic_records_path))
    parsed = []
    for raw in raw_rows:
        row = parse_clinic_record(raw)
        if row is not None:
            parsed.append(row)
    return parsed


def parse_clinic_record(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    if raw.get("resourceType") == "Bundle":
        return None
    if raw.get("resourceType") == "Patient":
        raw = _from_fhir_patient(raw)
    if any(isinstance(raw.get(key), dict) for key in ("patient_id", "_id", "hcp_id")):
        return None
    hcp_id = str(raw.get("hcp_id") or "").strip()
    first = str(raw.get("first_name") or "").strip()
    last = str(raw.get("last_name") or "").strip()
    if not hcp_id or not first or not last:
        return None
    if "/" in hcp_id or "\\" in hcp_id or ".." in hcp_id or hcp_id.startswith("$"):
        return None
    if isinstance(raw.get("patient_id"), dict) or isinstance(raw.get("_id"), dict) or isinstance(raw.get("hcp_id"), dict):
        return None
    external = str(raw.get("external_id") or raw.get("mrn") or raw.get("id") or "").strip()
    patient_id = str(raw.get("patient_id") or raw.get("_id") or "").strip()
    if not patient_id:
        patient_id = "pat_%s" % (external or ("%s_%s" % (hcp_id, last.lower())))
    if "/" in patient_id or "\\" in patient_id or ".." in patient_id or patient_id.startswith("$"):
        return None
    age = _as_int(raw.get("age"))
    if age is None and raw.get("birth_date"):
        age = _age_from_birth_date(str(raw.get("birth_date")))
    return {
        "_id": patient_id,
        "hcp_id": hcp_id,
        "external_id": external,
        "source": str(raw.get("source") or "clinic-export"),
        "first_name": first,
        "last_name": last,
        "age": age,
        "weight_kg": _as_float(raw.get("weight_kg")),
        "sex": str(raw.get("sex") or "").strip(),
        "medical_history": str(raw.get("medical_history") or "").strip(),
        "allergies": str(raw.get("allergies") or "").strip(),
        "current_medications": str(raw.get("current_medications") or "").strip(),
        "notes": str(raw.get("notes") or "").strip(),
    }


def _load_local(root: Path) -> List[Dict[str, Any]]:
    try:
        root = root.resolve()
    except OSError:
        return []
    if not root.is_dir():
        return []
    rows = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".json", ".txt"}:
            continue
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved != root and root not in resolved.parents:
            continue
        try:
            payload = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        rows.extend(_unwrap(payload))
    return rows


def _fetch_remote(url: str) -> List[Dict[str, Any]]:
    import requests

    headers = {}
    if settings.clinic_api_token:
        headers["Authorization"] = "Bearer %s" % settings.clinic_api_token
    response = requests.get(url, headers=headers, timeout=8)
    response.raise_for_status()
    return _unwrap(response.json())


def _unwrap(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    if payload.get("resourceType") == "Bundle":
        rows = []
        for entry in payload.get("entry") or []:
            resource = entry.get("resource") if isinstance(entry, dict) else None
            if isinstance(resource, dict):
                rows.append(resource)
        return rows
    if isinstance(payload.get("patients"), list):
        return [row for row in payload["patients"] if isinstance(row, dict)]
    return [payload]


def _from_fhir_patient(raw: Dict[str, Any]) -> Dict[str, Any]:
    name = {}
    names = raw.get("name") or []
    if names and isinstance(names[0], dict):
        name = names[0]
    given = name.get("given") or []
    first = given[0] if given else ""
    last = name.get("family") or ""
    hcp_id = ""
    for ref in raw.get("generalPractitioner") or []:
        if isinstance(ref, dict):
            ident = ref.get("identifier") or {}
            hcp_id = str(ident.get("value") or ref.get("reference") or "").replace("Practitioner/", "")
            if hcp_id:
                break
    chart = raw.get("chart") if isinstance(raw.get("chart"), dict) else {}
    gender = str(raw.get("gender") or chart.get("sex") or "").strip()
    sex = gender[:1].upper() + gender[1:] if gender else ""
    return {
        "patient_id": raw.get("patient_id") or ("pat_%s" % raw.get("id") if raw.get("id") else ""),
        "hcp_id": raw.get("hcp_id") or hcp_id,
        "external_id": raw.get("id") or raw.get("external_id"),
        "source": raw.get("source") or "fhir",
        "first_name": first,
        "last_name": last,
        "birth_date": raw.get("birthDate") or raw.get("birth_date"),
        "age": chart.get("age") or raw.get("age"),
        "weight_kg": chart.get("weight_kg") or raw.get("weight_kg"),
        "sex": sex,
        "medical_history": chart.get("medical_history") or raw.get("medical_history"),
        "allergies": chart.get("allergies") or raw.get("allergies"),
        "current_medications": chart.get("current_medications") or raw.get("current_medications"),
        "notes": chart.get("notes") or raw.get("notes"),
    }


def _as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _age_from_birth_date(value: str) -> Optional[int]:
    try:
        born = datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def records_for_hcp(records: Iterable[Dict[str, Any]], hcp_id: str) -> List[Dict[str, Any]]:
    return [row for row in records if row.get("hcp_id") == hcp_id]
