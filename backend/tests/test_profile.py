import pytest

from app.db.database import init_db
from app.db.seed import seed


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_get_profile_known_hcp_includes_seeded_familiarity(client):
    resp = client.get("/profile/hcp_amara")
    assert resp.status_code == 200
    body = resp.json()
    assert body["hcp_id"] == "hcp_amara"
    assert body["specialty"]
    assert body["familiarity"]["ibuprofen"] == "expert"  # seeded with touch_count=3


def test_get_profile_unknown_hcp_returns_404(client):
    resp = client.get("/profile/not_a_real_hcp")
    assert resp.status_code == 404
