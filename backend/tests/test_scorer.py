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


def test_primary_care_tiers_change_the_lead_passage():
    from app.retrieval.ingest import parse_dossier_fields

    for drug_id in ("biofreeze", "adderall"):
        fields = parse_dossier_fields(drug_id)
        rows = [
            build_summary_content(drug_id, tier, specialty="Primary Care")
            for tier in ("new", "returning", "expert")
        ]
        assert [row[0] for row in rows] == [
            "Primary Care · What it is",
            "Primary Care · Dosing & precautions",
            "Primary Care · Clinical profile",
        ]
        assert len({row[1][0] for row in rows}) == 3
        assert len({tuple(row[1]) for row in rows}) == 3
        dosing = fields["dosage_and_administration"]
        assert all(dosing in row[1] for row in rows)
