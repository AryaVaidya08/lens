from app.db.database import get_database
from app.db.seed import seed


def test_seed_is_idempotent(client):
    db = get_database()
    seed(db)
    seed(db)  # calling twice must not duplicate rows or error

    assert db.hcps.count_documents({"_id": {"$in": ["hcp_001", "hcp_002", "hcp_003"]}}) == 3
    assert db.drugs.count_documents({}) >= 3

    ibuprofen = db.drugs.find_one({"_id": "ibuprofen"})
    assert ibuprofen is not None

    expert_row = db.engagements.find_one({"touch_count": {"$gte": 2}})
    assert expert_row is not None, "seed data should include one pre-existing 'expert' engagement for the demo"

    for drug_id in ("adderall", "biofreeze", "lorazepam"):
        drug = db.drugs.find_one({"_id": drug_id})
        assert drug is not None, f"{drug_id} should be seeded"
        codes = [drug.get("barcode")] + list(drug.get("barcodes") or [])
        assert any(codes), f"{drug_id} should have a barcode"
