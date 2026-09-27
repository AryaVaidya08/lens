"""Follow-up questions stay grounded when startup corpus ingest was skipped."""

from app.config import settings
from app.llm import client as llm
from app.retrieval import index
from app.retrieval.index import retrieve
from tests.auth_util import login


def test_empty_index_loads_the_requested_dossier():
    saved = list(index.get_index())
    index.load([])
    try:
        assert index.chunk_count() == 0
        chunks = retrieve(
            "adderall",
            "Does this conflict with the patient's allergies or current medications?",
        )
        blob = "\n".join(chunks).lower()
        assert "hypersensitive" in blob
        assert "amphetamine" in blob
        loaded = index.chunk_count()
        assert loaded > 0
        retrieve("adderall", "what is the usual dose")
        assert index.chunk_count() == loaded

        topical = retrieve(
            "biofreeze",
            "Does this conflict with the patient's allergies?",
        )
        assert "sensitive" in "\n".join(topical).lower()
    finally:
        index.load(saved)


def test_ask_with_empty_index_passes_patient_chart(client, monkeypatch):
    import app.routes.drug as drug_route

    saved = list(index.get_index())
    index.load([])
    try:
        maya, _ = login(client, "hcp_001")
        seen = {}

        def fake_answer(query, context, tier="new", specialty=None, patient_context=None):
            seen["context"] = context
            seen["patient_context"] = patient_context
            return "Chart-aware answer."

        monkeypatch.setattr(drug_route, "generate_answer", fake_answer)
        resp = client.post(
            "/drug/adderall/ask",
            json={
                "hcp_id": "hcp_001",
                "query": "Does this conflict with the patient's allergies or current medications?",
                "patient_id": "pat_001",
            },
            headers=maya,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["answer_text"] == "Chart-aware answer."
        blob = "\n".join(seen["context"]).lower()
        assert "amphetamine" in blob
        chart = seen["patient_context"]
        assert "Penicillin" in chart
        assert "amphetamines" in chart
        assert "Metformin" in chart
        assert "72.5" in chart
        assert "Female" in chart
    finally:
        index.load(saved)


def test_ask_prompt_names_the_chart_and_bounds_tokens(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "She is 54, allergic to penicillin and amphetamines, "
                                "and takes metformin."
                            )
                        }
                    }
                ]
            }

    def post(url, **kwargs):
        captured["json"] = kwargs["json"]
        captured["timeout"] = kwargs["timeout"]
        assert url.endswith("/chat/completions")
        return Response()

    monkeypatch.setattr(llm.requests, "post", post)
    huge = "Hypersensitive to amphetamine. " + ("filler " * 4000)
    answer = llm.generate_answer(
        "Does this conflict with her allergies or current medications?",
        [huge],
        tier="new",
        specialty="Primary Care",
        patient_context=(
            "Patient: 54yo, Female, 72.5kg\n"
            "Allergies: Penicillin, amphetamines\n"
            "Current medications: Metformin 1000 mg BID"
        ),
    )
    assert "penicillin" in answer.lower()
    assert "metformin" in answer.lower()
    body = captured["json"]
    assert body["reasoning_effort"] == "low"
    assert body["max_tokens"] == llm._ASK_MAX_TOKENS
    assert captured["timeout"] == settings.llm_timeout_seconds
    user = body["messages"][1]["content"]
    system = body["messages"][0]["content"]
    assert "Selected patient chart:" in user
    assert "Penicillin" in user
    assert "54yo" in user
    assert "Metformin" in user
    assert "Drug reference context:" in user
    assert "Hypersensitive to amphetamine" in user
    assert len(user) < 8000
    assert "patient chart" in system.lower()
    assert "allergies" in system.lower()
