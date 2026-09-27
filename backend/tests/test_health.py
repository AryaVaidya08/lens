"""
The one real test in the stub set — /health is a real endpoint, not a
stub, so it gets a real test.
"""


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
