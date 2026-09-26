from app.db.database import SessionLocal, init_db
from app.db.models import Engagement
from app.personalization.scorer import score_familiarity, build_summary_content


def test_score_familiarity_thresholds():
    init_db()
    db = SessionLocal()
    try:
        db.query(Engagement).filter(
            Engagement.hcp_id == "hcp_score_test", Engagement.drug_id == "ibuprofen"
        ).delete()
        db.commit()

        assert score_familiarity("hcp_score_test", "ibuprofen") == "new"

        db.add(Engagement(hcp_id="hcp_score_test", drug_id="ibuprofen", touch_count=1))
        db.commit()
        assert score_familiarity("hcp_score_test", "ibuprofen") == "returning"

        db.query(Engagement).filter(
            Engagement.hcp_id == "hcp_score_test", Engagement.drug_id == "ibuprofen"
        ).update({"touch_count": 3})
        db.commit()
        assert score_familiarity("hcp_score_test", "ibuprofen") == "expert"
    finally:
        db.query(Engagement).filter(
            Engagement.hcp_id == "hcp_score_test", Engagement.drug_id == "ibuprofen"
        ).delete()
        db.commit()
        db.close()


def test_build_summary_content_differs_by_tier():
    new_headline, new_bullets = build_summary_content("ibuprofen", "new")
    expert_headline, expert_bullets = build_summary_content("ibuprofen", "expert")

    assert new_bullets != expert_bullets
    assert len(new_bullets) > 0
    assert len(expert_bullets) > 0
    assert isinstance(new_headline, str) and new_headline
