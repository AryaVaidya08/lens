import pytest

from app.db.database import init_db
from app.db.seed import seed
import app.routes.drug as drug_route


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_full_scan_ask_rescan_flow(client, monkeypatch):
    # 1. iOS detects a package via barcode.
    detect_resp = client.post("/detect", json={"barcode": "3-00000-00171", "ocr_text": None})
    assert detect_resp.status_code == 200
    drug_id = detect_resp.json()["drug_id"]
    assert drug_id == "ibuprofen"

    hcp_id = "hcp_priya"  # seeded with no prior engagement -> "new"

    # 2. First summary: should be "new" tier.
    summary1 = client.get(f"/drug/{drug_id}/summary", params={"hcp_id": hcp_id}).json()
    assert summary1["tier"] == "new"

    # 3. Voice follow-up question, grounded in the real RAG index — mock the
    #    LLM call itself so this test has no network/API-key dependency.
    monkeypatch.setattr(
        drug_route, "generate_answer", lambda query, context: f"Mock answer using {len(context)} sources."
    )
    ask_resp = client.post(f"/drug/{drug_id}/ask", json={"hcp_id": hcp_id, "query": "What is this used for?"})
    assert ask_resp.status_code == 200
    assert "answer_text" in ask_resp.json()

    # 4. Log engagement 3 times (crosses the "expert" threshold).
    log_resp = None
    for _ in range(3):
        log_resp = client.post("/engagement/log", json={"hcp_id": hcp_id, "drug_id": drug_id})
        assert log_resp.status_code == 200
    assert log_resp.json()["touch_count"] == 3

    # 5. Second summary: same HCP, same drug, must now be visibly different.
    summary2 = client.get(f"/drug/{drug_id}/summary", params={"hcp_id": hcp_id}).json()
    assert summary2["tier"] == "expert"
    assert summary2["bullets"] != summary1["bullets"]

    # 6. Profile now reflects the updated tier too.
    profile_resp = client.get(f"/profile/{hcp_id}")
    assert profile_resp.json()["familiarity"][drug_id] == "expert"
