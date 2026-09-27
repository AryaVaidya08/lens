from tests.auth_util import login


def test_demo_hcp_types_get_different_adderall_summaries(client, monkeypatch):
    import app.routes.drug as drug_route

    def summarize(name, passages, tier, specialty):
        return [f"{specialty} {tier} lead from {passages[0][:40]}"], "grok"

    monkeypatch.setattr(drug_route, "summarize_scan", summarize)
    maya, maya_body = login(client, "hcp_001")
    james, james_body = login(client, "hcp_002")
    sofia, sofia_body = login(client, "hcp_003")
    assert maya_body["specialty"] == "Primary Care"
    assert james_body["specialty"] == "Cardiology"
    assert sofia_body["specialty"] == "Endocrinology"

    def summary(headers, hcp_id):
        return client.get(
            "/drug/adderall/summary",
            params={"hcp_id": hcp_id},
            headers=headers,
        ).json()

    maya_sum = summary(maya, "hcp_001")
    james_sum = summary(james, "hcp_002")
    sofia_sum = summary(sofia, "hcp_003")
    assert maya_sum["tier"] == "new"
    assert james_sum["tier"] == "new"
    assert sofia_sum["tier"] == "new"
    assert "Primary Care" in maya_sum["headline"]
    assert "Cardiology" in james_sum["headline"]
    assert "Endocrinology" in sofia_sum["headline"]
    assert "What it is" in maya_sum["headline"]
    assert len({tuple(maya_sum["bullets"]), tuple(james_sum["bullets"]), tuple(sofia_sum["bullets"])}) > 1


def test_ask_passes_authenticated_specialty(client, monkeypatch):
    import app.routes.drug as drug_route

    seen = []

    monkeypatch.setattr(
        drug_route,
        "retrieve",
        lambda drug_id, query, specialty=None: ["Dosing 5 mg. Interactions with stimulants."],
    )

    def fake_answer(query, context, tier="new", specialty=None, patient_context=None):
        seen.append(specialty)
        return "Answer for %s" % specialty

    monkeypatch.setattr(drug_route, "generate_answer", fake_answer)
    maya, _ = login(client, "hcp_001")
    james, _ = login(client, "hcp_002")
    assert (
        client.post(
            "/drug/adderall/ask",
            json={"hcp_id": "hcp_001", "query": "how should I dose this"},
            headers=maya,
        ).json()["answer_text"]
        == "Answer for Primary Care"
    )
    assert (
        client.post(
            "/drug/adderall/ask",
            json={"hcp_id": "hcp_002", "query": "how should I dose this"},
            headers=james,
        ).json()["answer_text"]
        == "Answer for Cardiology"
    )
    assert seen == ["Primary Care", "Cardiology"]


def test_summary_reflects_seeded_expert_tier(client, monkeypatch):
    import app.routes.drug as drug_route

    monkeypatch.setattr(
        drug_route,
        "summarize_scan",
        lambda name, passages, tier, specialty: ([f"{tier}: {passages[0][:48]}"], "grok"),
    )
    headers, _ = login(client, "hcp_002")
    resp = client.get("/drug/lorazepam/summary", params={"hcp_id": "hcp_002"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "expert"
    assert "Clinical profile" in body["headline"]
    assert body["summary_source"] == "grok"
    assert len(body["bullets"]) > 0
    assert body["full_bullets"] == []


def test_summary_new_hcp_gets_new_tier_and_different_content(client, monkeypatch):
    import app.routes.drug as drug_route

    monkeypatch.setattr(
        drug_route,
        "summarize_scan",
        lambda name, passages, tier, specialty: ([f"{tier}|{passages[0][:60]}"], "grok"),
    )
    expert, _ = login(client, "hcp_002")
    newbie, _ = login(client, "hcp_003")
    expert_resp = client.get("/drug/lorazepam/summary", params={"hcp_id": "hcp_002"}, headers=expert)
    new_resp = client.get("/drug/lorazepam/summary", params={"hcp_id": "hcp_003"}, headers=newbie)
    assert new_resp.json()["tier"] == "new"
    assert expert_resp.json()["tier"] == "expert"
    assert "What it is" in new_resp.json()["headline"]
    assert "Clinical profile" in expert_resp.json()["headline"]
    assert new_resp.json()["bullets"] != expert_resp.json()["bullets"]


def test_summary_unknown_drug_returns_404(client):
    headers, _ = login(client, "hcp_001")
    resp = client.get("/drug/not_a_real_drug/summary", params={"hcp_id": "hcp_001"}, headers=headers)
    assert resp.status_code == 404
