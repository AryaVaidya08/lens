import json

import pytest
import requests

from app.llm import client as llm
from app.config import settings
from tests.auth_util import login


def response(sections, finish="stop"):
    """Build a structured scan response. A flat list is one passage."""
    if sections and isinstance(sections[0], str):
        sections = [sections]
    payload = {"sections": [{"bullets": group} for group in sections]}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"finish_reason": finish, "message": {"content": json.dumps(payload)}}]}
    return Response()


def three(prefix):
    return [
        f"{prefix} covers the labeled audience.",
        f"{prefix} states the dose and duration.",
        f"{prefix} says when to stop use.",
    ]


def test_full_selected_passages_go_to_grok_with_personalization(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    passages = ["Reference detail. " * 200, "Second reference section."]
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        assert url.endswith("/chat/completions")
        prompt = json.loads(kwargs["json"]["messages"][1]["content"])
        assert prompt["drug"] == "Example"
        assert prompt["specialty"] == "Cardiology"
        assert prompt["familiarity"] == "returning"
        assert prompt["passages"] == [p.strip() for p in passages]
        assert "rewrite" in prompt["task"].lower()
        assert "3" in prompt["task"] and "4" in prompt["task"]
        system = kwargs["json"]["messages"][0]["content"]
        assert "3" in system and "4" in system
        assert "28" in system
        schema = kwargs["json"]["response_format"]["json_schema"]
        assert schema["strict"]
        sections = schema["schema"]["properties"]["sections"]
        assert sections["minItems"] == sections["maxItems"] == len(prompt["passages"])
        bullet_schema = sections["items"]["properties"]["bullets"]
        assert bullet_schema["minItems"] == 3
        assert bullet_schema["maxItems"] == 4
        assert kwargs["json"]["max_tokens"] == llm._SCAN_MAX_TOKENS
        assert kwargs["json"]["reasoning_effort"] == "low"
        assert kwargs["timeout"] == settings.llm_timeout_seconds
        return response([three("First passage"), three("Second passage") + ["First passage names a boxed warning."]])

    monkeypatch.setattr(llm.requests, "post", post)
    expected_bullets = three("First passage") + three("Second passage") + ["First passage names a boxed warning."]
    expected = (expected_bullets, "grok")
    assert llm.summarize_scan("Example", passages, "returning", "Cardiology") == expected
    assert llm.summarize_scan("Example", passages, "returning", "Cardiology") == expected
    assert len(calls) == 1


def test_cache_separates_tier_specialty_source_and_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    calls = []
    def post(url, **kwargs):
        calls.append(kwargs)
        return response(three("Cached passage"))
    monkeypatch.setattr(llm.requests, "post", post)
    for tier, specialty, source in [
        ("new", "Cardiology", "Source"), ("returning", "Cardiology", "Source"),
        ("expert", "Cardiology", "Source"), ("expert", "Pediatrics", "Source"),
        ("expert", "Pediatrics", "Updated source"),
    ]:
        assert llm.summarize_scan("Example", [source], tier, specialty)[1] == "grok"
    monkeypatch.setattr(settings, "llm_model", "another-model")
    llm.summarize_scan("Example", ["Updated source"], "expert", "Pediatrics")
    assert len(calls) == 6


@pytest.mark.parametrize("bullets,finish", [
    ([], "stop"), ([""], "stop"), ([123], "stop"),
    (["x" * 181, "Second distinct fact.", "Third distinct fact."], "stop"),
    (["word " * 29, "Second distinct fact.", "Third distinct fact."], "stop"),
    (["One", "Two"], "stop"),
    (["One.", "Two.", "Three.", "Four.", "Five."], "stop"),
    (["Valid but incomplete", "Second distinct fact.", "Third distinct fact."], "length"),
])
def test_invalid_model_output_does_not_leak_reference_text(monkeypatch, bullets, finish):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: response(bullets, finish))
    result, source = llm.summarize_scan("Example", ["Reference material. " * 80], "new", "General")
    assert source == "unavailable"
    assert result == []


def test_timeout_is_not_cached_and_retry_can_succeed(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    def timeout(*args, **kwargs):
        raise requests.Timeout()
    monkeypatch.setattr(llm.requests, "post", timeout)
    assert llm.summarize_scan("Example", ["Source"], "new", "General")[1] == "unavailable"
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: response(three("Retry")))
    assert llm.summarize_scan("Example", ["Source"], "new", "General")[1] == "grok"


def test_missing_key_never_calls_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("A missing key must not cause a network call")
    monkeypatch.setattr(llm.requests, "post", forbidden)
    assert llm.summarize_scan("Example", ["Reference."], "new", "General") == ([], "unavailable")


@pytest.mark.parametrize("content", [
    "not JSON", "null", '{"bullets": "text"}', '{"bullets": ["Same", "Same"]}',
    json.dumps({"sections": [
        {"bullets": ["Same fact.", "Second fact.", "Third fact."]},
        {"bullets": ["Same fact.", "Fourth fact.", "Fifth fact."]},
    ]}),
])
def test_malformed_or_duplicate_bullets_are_not_displayed(monkeypatch, content):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Response())
    assert llm.summarize_scan("Example", ["First source.", "Second source."], "new", "General")[1] == "unavailable"


def test_copied_source_sentences_are_rejected(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    source = "This medication is indicated for attention deficit hyperactivity disorder in adults and children."
    monkeypatch.setattr(
        llm.requests,
        "post",
        lambda *a, **k: response([
            source[:80],
            "Children need a clinician's advice before starting.",
            "Adults should follow the labeled dose and duration.",
        ]),
    )
    assert llm.summarize_scan("Example", [source], "new", "General")[1] == "unavailable"


def test_real_sentence_bounds_accept_28_words_and_180_characters(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    source = "Original label passage that must not be copied into the summary."
    words = " ".join(["fact"] * 28)
    chars = "z" * 180
    monkeypatch.setattr(
        llm.requests,
        "post",
        lambda *a, **k: response([
            words,
            chars,
            "Stop use if the labeled warning appears.",
            "Adults are the labeled audience for this dose.",
        ]),
    )
    bullets, source_name = llm.summarize_scan("Example", [source], "new", "General")
    assert source_name == "grok"
    assert bullets == [
        words,
        chars,
        "Stop use if the labeled warning appears.",
        "Adults are the labeled audience for this dose.",
    ]
    assert len(bullets[0].split()) == 28
    assert len(bullets[1]) == 180


def test_http_failure_is_not_a_successful_summary(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    def failed(*args, **kwargs):
        raise requests.HTTPError("provider rejected request")
    monkeypatch.setattr(llm.requests, "post", failed)
    assert llm.summarize_scan("Example", ["Source."], "new", "General")[1] == "unavailable"


def test_summary_route_returns_generated_bullets_and_original_references(client, monkeypatch):
    import app.routes.drug as route
    seen = []
    def summarize(name, passages, tier, specialty):
        seen.append((passages, tier, specialty))
        return ["Generated compact bullet."], "grok"
    monkeypatch.setattr(route, "summarize_scan", summarize)
    headers, _ = login(client, "hcp_001")
    result = client.get("/drug/adderall/summary", params={"hcp_id": "hcp_001"}, headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["bullets"] == ["Generated compact bullet."]
    assert body["summary_source"] == "grok"
    assert body["full_bullets"] == []
    assert seen[0][0]
    assert seen[0][1:] == (body["tier"], "Primary Care")
    assert "Generated compact bullet." not in "".join(seen[0][0])


def test_summary_route_never_returns_source_passages(client):
    headers, _ = login(client, "hcp_001")
    body = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": "hcp_001", "patient_id": "pat_001"},
        headers=headers,
    ).json()
    assert body["full_bullets"] == []
    assert body["summary_source"] == "unavailable"
    assert body["bullets"] == []
    blob = " ".join(body["bullets"]).lower()
    assert "amphetamine" not in blob
    assert "indication" not in blob


def test_patient_scan_summarizes_without_sending_chart(client, monkeypatch):
    import app.routes.drug as route
    seen = []

    def summarize(name, passages, tier, specialty):
        seen.append((name, passages, tier, specialty))
        blob = " ".join(passages).lower()
        assert "elena" not in blob
        assert "vasquez" not in blob
        assert "penicillin" not in blob
        return ["Short Grok bullet."], "grok"

    monkeypatch.setattr(route, "summarize_scan", summarize)
    headers, _ = login(client, "hcp_001")
    response = client.get(
        "/drug/adderall/summary",
        params={"hcp_id": "hcp_001", "patient_id": "pat_001"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["patient_check"]["patient_id"] == "pat_001"
    assert body["bullets"] == ["Short Grok bullet."]
    assert body["summary_source"] == "grok"
    assert seen
