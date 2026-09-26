"""Login, sync clinic, check HUD flags, store an access case, confirm Mongo."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from uuid import uuid4

BASE = "http://127.0.0.1:8000"


def request(method: str, path: str, token: str | None = None, body: dict | None = None, query: str = "") -> tuple[int, dict]:
    url = BASE + path + query
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"detail": raw.decode("utf-8", "replace")}
        return exc.code, parsed


def main() -> int:
    status, health = request("GET", "/health")
    if status != 200:
        print("backend down")
        return 1
    _, info = request("GET", "/status")
    print("db", info.get("mongodb_db"), info.get("mongodb_kind"))

    code, login = request(
        "POST",
        "/auth/login",
        body={"email": "maya.patel@lens.demo", "password": "demo"},
    )
    if code != 200:
        print("login failed", code)
        return 1
    token = login["session_token"]

    code, synced = request("POST", "/patients/sync", token)
    print("sync", code, "imported", synced.get("imported"))

    code, elena = request("GET", "/patients/pat_001", token)
    print("elena allergies", elena.get("allergies"), "dob", elena.get("birth_date"))

    code, summary = request(
        "GET",
        "/drug/adderall/summary",
        token,
        query="?hcp_id=hcp_001&patient_id=pat_001",
    )
    if "patient_check" not in summary:
        print("live server is on old code; restart uvicorn to load scan check")
        return 2
    check = summary.get("patient_check") or {}
    prefill = summary.get("access_prefill") or {}
    print("check", check.get("status"), check.get("flags"))
    print("prefill", prefill.get("medication"), prefill.get("strength"), prefill.get("formulation"))

    case_id = str(uuid4())
    code, saved = request(
        "PUT",
        "/patients/pat_001/medication-access/" + case_id,
        token,
        body={
            "medication": prefill.get("medication") or "Adderall",
            "strength": prefill.get("strength") or "",
            "formulation": prefill.get("formulation") or "",
            "indication": prefill.get("indication") or "",
            "medication_source": "Lens scan · Adderall",
            "patient_dob": elena.get("birth_date") or "",
            "prescriber": "Dr. Maya Patel",
        },
    )
    print("save access", code, "case", saved.get("case_id"), "med", saved.get("medication"))
    if code != 200:
        print(saved)
        return 1

    code, listed = request("GET", "/patients/pat_001/medication-access", token)
    ids = [row.get("case_id") for row in listed.get("cases", [])]
    print("listed", case_id in ids, "count", len(ids))

    code, logged = request(
        "POST",
        "/engagement/log",
        token,
        body={"hcp_id": "hcp_001", "drug_id": "adderall", "patient_id": "pat_001"},
    )
    print("engagement", code, logged)
    return 0 if check.get("status") == "flag" and case_id in ids else 1


if __name__ == "__main__":
    sys.exit(main())
