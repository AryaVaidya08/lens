"""
The LLM swap point.

Wraps the LLM API used by the backend. Nothing else in the codebase
should call the LLM API directly.

Owned by: Voice & LLM lane.
"""

from __future__ import annotations

import re
from typing import Optional

import requests

from app.config import settings
from app.text import content_terms


# Answers are spoken aloud by AVSpeechSynthesizer, so length is constrained
# in the prompt rather than by truncating mid-sentence.
_SENTENCES_BY_TIER = {
    "new": 2,
    "returning": 3,
    "expert": 4,
}

_SYSTEM_PROMPT = (
    "You are a clinical reference assistant speaking to a {specialty} clinician. "
    "Answer only from the provided context; if the context does not cover "
    "the question, say so in one sentence. Never invent dosing, trial "
    "results, or safety claims. Reply in at most {sentences} short sentences "
    "of plain prose, with no lists or markdown, because the reply is read "
    "aloud. The clinician's familiarity with this drug is '{tier}': for "
    "'new' lead with the basics, for 'returning' provide a moderate level "
    "of detail, and for 'expert' skip the basics and lead with dosing, "
    "trial data, and interactions when those details are present in the "
    "provided context. Prefer facts that matter for {specialty} practice "
    "when they appear in the context."
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_NOT_COVERED = (
    "I don't have anything on that in this drug's reference material."
)


def generate_answer(
    query: str,
    context: list[str],
    tier: str = "new",
    specialty: str | None = None,
) -> str:
    """
    Generate a spoken-ready answer to `query`, grounded only in `context`.

    This is the single LLM swap point for the application. Retrieval happens
    before this function is called.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query cannot be empty")

    if not context:
        return _NOT_COVERED

    # Normalize unexpected tier values rather than allowing them to alter
    # the prompt in an uncontrolled way.
    if tier not in _SENTENCES_BY_TIER:
        tier = "new"

    # Grok/xAI is the active provider. If no key is configured, use the
    # grounded local fallback instead of failing the demo.
    if settings.llm_enabled:
        answer = _call_llm(query, context, tier, specialty)
        if answer:
            return answer

    return _extractive_answer(query, context, tier, specialty)


def _call_llm(
    query: str,
    context: list[str],
    tier: str,
    specialty: str | None = None,
) -> Optional[str]:
    """
    Call the configured xAI-compatible chat-completions endpoint.

    Returns None on any API/network/response-format failure so the caller
    can fall back to a grounded extractive answer.
    """
    sentences = _SENTENCES_BY_TIER.get(tier, 2)

    joined = "\n\n".join(
        f"[Source {i + 1}]\n{chunk}"
        for i, chunk in enumerate(context)
    )

    system_prompt = _SYSTEM_PROMPT.format(
        sentences=sentences,
        tier=tier,
        specialty=(specialty or "").strip() or "general",
    )

    user_prompt = (
        "Drug information context:\n\n"
        f"{joined}\n\n"
        f"Question:\n{query}"
    )

    try:
        response = requests.post(
            f"{settings.llm_api_base.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
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
            timeout=settings.llm_timeout_seconds,
        )

        response.raise_for_status()

        data = response.json()

        answer = data["choices"][0]["message"]["content"]

        if not isinstance(answer, str):
            return None

        answer = " ".join(answer.split())

        return answer or None

    except Exception:
        # The fallback is deliberately silent. A temporary API/network
        # failure should not make the demo unusable.
        return None


def _extractive_answer(
    query: str,
    context: list[str],
    tier: str,
    specialty: str | None = None,
) -> str:
    """
    Produce a grounded fallback answer directly from retrieved context.

    Retrieval has already selected the relevant drug section. The section
    prose is lead-first, so its opening sentences are generally the most
    useful material to read aloud.
    """
    query_terms = set(content_terms(query))

    if query_terms and not any(
        query_terms & set(content_terms(chunk))
        for chunk in context
    ):
        return _NOT_COVERED

    wanted = _SENTENCES_BY_TIER.get(tier, 2)

    chosen: list[str] = []
    chosen_terms: list[set[str]] = []

    for sentence in _SENTENCE_SPLIT.split(context[0]):
        sentence = sentence.strip()

        if len(sentence) < 25:
            continue

        terms = set(content_terms(sentence))

        # Avoid repeating nearly identical sentences, which can happen when
        # a dossier contains prose followed by bullets covering the same fact.
        if any(
            terms and len(terms - seen) <= 1
            for seen in chosen_terms
        ):
            continue

        chosen.append(sentence)
        chosen_terms.append(terms)

        if len(chosen) == wanted:
            break

    return " ".join(chosen) if chosen else _NOT_COVERED