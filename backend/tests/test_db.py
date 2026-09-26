from app.db.database import SessionLocal, init_db, engine
from app.db.models import HCP


def test_init_db_creates_tables():
    init_db()
    db = SessionLocal()
    try:
        db.add(HCP(id="hcp_test", name="Dr. Test", specialty="Cardiology"))
        db.commit()
        found = db.query(HCP).filter(HCP.id == "hcp_test").first()
        assert found is not None
        assert found.name == "Dr. Test"
    finally:
        db.query(HCP).filter(HCP.id == "hcp_test").delete()
        db.commit()
        db.close()
