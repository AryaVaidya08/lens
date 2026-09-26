"""
The LLM swap point.

Wraps whichever LLM API is used (sponsor API for the hackathon).
Nothing else in the codebase should call the LLM API directly — see
docs/architecture.md's scaling table for why this stays isolated.

Owned by: Voice & LLM lane.
"""

import re
from typing import Optional

import requests

from app.config import settings
from app.text import content_terms

# Answers are spoken aloud by AVSpeechSynthesizer, so length is constrained in
# the prompt rather than by truncating (truncation cuts off mid-sentence).
_SENTENCES_BY_TIER = {"new": 2, "returning": 3, "expert": 4}

_SYSTEM_PROMPT = (
    "You are a clinical reference assistant speaking to a physician. Answer only "
    "from the provided context; if the context does not cover the question, say so "
    "in one sentence. Never invent dosing, trial results, or safety claims. Reply in "
    "at most {sentences} short sentences of plain prose, with no lists or markdown, "
    "because the reply is read aloud. The physician's familiarity with this drug is "
    "'{tier}': for 'new' lead with the basics, for 'expert' skip the basics and lead "
    "with dosing, trial data, and interactions."
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_NOT_COVERED = "I don't have anything on that in this drug's reference material."


def generate_answer(query: str, context: list[str], tier: str = "new") -> str:
    """
    Generates a spoken-ready answer to `query`, grounded in `context`
    (the chunks returned by retrieval/index.py::retrieve).

    Falls back to an extractive answer built from the same context when no LLM
    key is configured or the API call fails, so the demo never dead-ends on a
    network problem. Either way the answer is grounded in `context` only.
    """
    if not context:
        return "I don't have anything on that in this drug's reference material."

    if settings.llm_enabled:
        answer = _call_llm(query, context, tier)
        if answer:
            return answer
    return _extractive_answer(query, context, tier)


def _call_llm(query: str, context: list[str], tier: str) -> Optional[str]:
    sentences = _SENTENCES_BY_TIER.get(tier, 3)
    joined = "\n\n".join(f"[{i + 1}] {chunk}" for i, chunk in enumerate(context))
    try:
        response = requests.post(
            f"{settings.llm_api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "system",
                        "content": _SYSTEM_PROMPT.format(sentences=sentences, tier=tier),
                    },
                    {"role": "user", "content": f"Context:\n{joined}\n\nQuestion: {query}"},
                ],
            },
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return " ".join(content.split()) or None
    except Exception:
        # Any API problem falls through to the grounded extractive answer.
        return None


def _extractive_answer(query: str, context: list[str], tier: str) -> str:
    """
    Reads back the opening of the best-matching section.

    Retrieval has already chosen the right section, and each section's prose is
    written lead-first, so its opening sentences are both the most relevant
    answer and the only part that reads well aloud — the trailing bullets are
    fragments. The tier decides how many sentences to read.
    """
    query_terms = set(content_terms(query))
    if query_terms and not any(query_terms & set(content_terms(chunk)) for chunk in context):
        # Nothing in this drug's dossier touches the question. Say so rather
        # than reciting an unrelated section — this is pharma-facing.
        return _NOT_COVERED

    wanted = _SENTENCES_BY_TIER.get(tier, 3)
    chosen: list[str] = []
    chosen_terms: list[set] = []
    for sentence in _SENTENCE_SPLIT.split(context[0]):
        sentence = sentence.strip()
        if len(sentence) < 25:
            continue
        terms = set(content_terms(sentence))
        # Each section restates its prose as bullets, so skip a sentence whose
        # content is already covered — otherwise the answer repeats itself.
        if any(terms and len(terms - seen) <= 1 for seen in chosen_terms):
            continue
        chosen.append(sentence)
        chosen_terms.append(terms)
        if len(chosen) == wanted:
            break

    return " ".join(chosen) if chosen else _NOT_COVERED
