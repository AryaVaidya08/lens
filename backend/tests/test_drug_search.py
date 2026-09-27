"""Covers the /drug/search picker and the drug_name field on chat history,
both added so the frontend's Drug Information view can auto-populate from
real backend data instead of a static fixture."""

from tests.auth_util import login


def test_search_requires_auth(client):
    assert client.get("/drug/search?q=adder").status_code == 401


def test_search_matches_by_name_case_insensitively(client):
    headers, _ = login(client, "hcp_001")

    response = client.get("/drug/search?q=aDDeral", headers=headers)
    assert response.status_code == 200

    drugs = response.json()["drugs"]
    assert any(item["drug_id"] == "adderall" for item in drugs)
    assert all("name" in item and "drug_id" in item for item in drugs)


def test_search_empty_query_returns_a_page_of_results(client):
    headers, _ = login(client, "hcp_001")

    response = client.get("/drug/search", headers=headers)
    assert response.status_code == 200

    drugs = response.json()["drugs"]
    assert len(drugs) > 0
    assert len(drugs) <= 25


def test_search_limit_is_capped(client):
    headers, _ = login(client, "hcp_001")

    response = client.get("/drug/search?limit=9999", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["drugs"]) <= 50


def test_chats_include_drug_name(client):
    headers, _ = login(client, "hcp_001")

    asked = client.post(
        "/drug/adderall/ask",
        json={"hcp_id": "hcp_001", "query": "What are conflicting medications?"},
        headers=headers,
    )
    assert asked.status_code == 200

    chats = client.get("/profile/hcp_001/chats", headers=headers).json()["chats"]
    match = next(chat for chat in chats if chat["drug_id"] == "adderall")
    assert match["drug_name"] == "Adderall"
