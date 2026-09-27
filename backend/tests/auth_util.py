DEMO_LOGINS = {
    "hcp_001": ("maya.patel@lens.demo", "demo"),
    "hcp_002": ("james.chen@lens.demo", "demo"),
    "hcp_003": ("sofia.ramirez@lens.demo", "demo"),
}


def login(client, hcp_id="hcp_001"):
    email, password = DEMO_LOGINS[hcp_id]
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "password_hash" not in body
    assert "recovery_hash" not in body
    return {"Authorization": "Bearer " + body["session_token"]}, body
