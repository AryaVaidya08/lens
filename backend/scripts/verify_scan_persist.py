"""Login, sync clinic, check HUD flags, and confirm engagement persist."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

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
    print("check", check.get("status"), check.get("flags"))

    code, logged = request(
        "POST",
        "/engagement/log",
        token,
        body={"hcp_id": "hcp_001", "drug_id": "adderall", "patient_id": "pat_001"},
    )
    print("engagement", code, logged)
    return 0 if check.get("status") == "flag" else 1


if __name__ == "__main__":
    sys.exit(main())
