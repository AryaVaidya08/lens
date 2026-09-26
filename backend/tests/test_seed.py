from app.db.database import SessionLocal, init_db
from app.db.seed import seed
from app.db.models import HCP, Drug, Engagement


def test_seed_is_idempotent():
    init_db()
    seed()
    seed()  # calling twice must not duplicate rows or error

    db = SessionLocal()
    try:
        assert db.query(HCP).count() >= 3
        assert db.query(Drug).count() >= 3
        ibuprofen = db.query(Drug).filter(Drug.id == "ibuprofen").first()
        assert ibuprofen is not None
        assert ibuprofen.barcode is not None

        expert_row = db.query(Engagement).filter(Engagement.touch_count >= 3).first()
        assert expert_row is not None, "seed data should include one pre-existing 'expert' engagement for the demo"

        for drug_id in ("adderall", "biofreeze", "lorazepam"):
            drug = db.query(Drug).filter(Drug.id == drug_id).first()
            assert drug is not None, f"{drug_id} should be seeded"
            assert drug.barcode is not None
    finally:
        db.close()
