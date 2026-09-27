from app.db.database import get_database


def test_mongo_accepts_and_finds_hcp_row():
    db = get_database()
    db.hcps.delete_one({"_id": "hcp_test"})
    db.hcps.insert_one({"_id": "hcp_test", "name": "Dr. Test", "specialty": "Cardiology"})
    try:
        found = db.hcps.find_one({"_id": "hcp_test"})
        assert found is not None
        assert found["name"] == "Dr. Test"
    finally:
        db.hcps.delete_one({"_id": "hcp_test"})
