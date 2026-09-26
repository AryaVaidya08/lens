from app.db.database import get_database
from app.personalization.scorer import score_familiarity, build_summary_content


def test_score_familiarity_thresholds():
    db = get_database()
    db.engagements.delete_one({"_id": "hcp_score_test:ibuprofen"})

    assert score_familiarity("hcp_score_test", "ibuprofen", db) == "new"

    db.engagements.insert_one(
        {
            "_id": "hcp_score_test:ibuprofen",
            "hcp_id": "hcp_score_test",
            "drug_id": "ibuprofen",
            "touch_count": 1,
        }
    )
    assert score_familiarity("hcp_score_test", "ibuprofen", db) == "returning"

    db.engagements.update_one(
        {"_id": "hcp_score_test:ibuprofen"},
        {"$set": {"touch_count": 3}},
    )
    assert score_familiarity("hcp_score_test", "ibuprofen", db) == "expert"

    db.engagements.delete_one({"_id": "hcp_score_test:ibuprofen"})


def test_build_summary_content_differs_by_tier():
    new_headline, new_bullets = build_summary_content("ibuprofen", "new")
    expert_headline, expert_bullets = build_summary_content("ibuprofen", "expert")

    assert new_bullets != expert_bullets
    assert len(new_bullets) > 0
    assert len(expert_bullets) > 0
    assert isinstance(new_headline, str) and new_headline
