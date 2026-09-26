"""
The LLM swap point.

Wraps whichever LLM API is used (OpenAI for now).
Nothing else in the codebase should call the LLM API directly — see
docs/architecture.md's scaling table for why this stays isolated.

Owned by: Voice & LLM lane.
"""

import requests
from openai import OpenAI

from ..config import settings


def generate_answer(query: str, context: list[str]) -> str:
    """
    Generates a spoken-ready answer to `query`, grounded in `context`
    (the chunks returned by retrieval/index.py::retrieve).
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query cannot be empty")

    if not context:
        raise ValueError("No retrieval context was provided")

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    context_text = "\n\n".join(
        f"[Source {i + 1}]\n{chunk}"
        for i, chunk in enumerate(context)
    )

    system_prompt = """
You are an HCP drug-information assistant.

Answer the user's question using ONLY the provided drug-information
context.

Do not use outside knowledge or invent clinical facts.

If the provided context does not contain enough information to answer
the question, say that the available drug information does not contain
the answer.

Keep the answer concise and suitable for being spoken aloud.
Do not mention the retrieval process or these instructions.
"""

    user_prompt = f"""
Drug information context:

{context_text}

Question:
{query}
"""
    # ================================================================
    # ACTIVE: GROK / XAI
    # ================================================================


    if not settings.llm_api_key:
        raise RuntimeError("XAI_API_KEY is not configured")

    response = requests.post(
        f"{settings.llm_api_base}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "grok-4.7",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "temperature": 0.2,
        },
        timeout=20,
    )

    if not response.ok:
        raise RuntimeError(
            f"LLM Request Failed: {response.status_code} - {response.text}"
        )

    data = response.json()

    try:
        answer = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        raise RuntimeError("LLM API returned an invalid response")

    if not answer:
        raise RuntimeError("LLM API returned an empty answer")

    return answer
"""
    # ================================================================
    # BACKUP: OPENAI
    # ================================================================

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=system_prompt,
            input=user_prompt,
        )

    except Exception as exc:
        raise RuntimeError(f"OpenAI request failed: {exc}") from exc

    answer = response.output_text.strip()

    if not answer:
        raise RuntimeError("OpenAI API returned an empty answer")

    return answer
"""
