"""
The LLM swap point.

Wraps the LLM API used by the backend. Nothing else in the codebase
should call the LLM API directly.

Owned by: Voice & LLM lane.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
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
    "Answer only from the drug reference context and, when a selected patient "
    "chart is included, from that chart. If those materials do not cover the "
    "question, say so in one sentence. Never invent dosing, trial results, "
    "safety claims, or chart facts. When a selected patient chart is included "
    "and the question concerns that patient, name the relevant listed facts "
    "(age, sex, weight, allergies, current medications) and relate them to "
    "the drug reference, including when the reference does not mention that "
    "allergen or medication. Reply in at most {sentences} short sentences "
    "of plain prose, with no lists or markdown, because the reply is read "
    "aloud. The clinician's familiarity with this drug is '{tier}': for "
    "'new' lead with the basics, for 'returning' provide a moderate level "
    "of detail, and for 'expert' skip the basics and lead with dosing, "
    "trial data, and interactions when those details are present in the "
    "drug reference. Prefer facts that matter for {specialty} practice "
    "when they appear in the drug reference."
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_NOT_COVERED = (
    "I don't have anything on that in this drug's reference material."
)
_ASK_UNAVAILABLE = (
    "I couldn't generate an answer from the reference material right now."
)


_SCAN_PROMPT_VERSION = "rewrite-v3"
_MAX_BULLET_CHARS = 180
_MAX_BULLET_WORDS = 28
_BULLETS_PER_PASSAGE = (3, 4)
# Three passages × four sentences is roughly 500 tokens, plus a little
# low-effort reasoning. Keep the cap bounded: uncapped grok-4.7 reasoning
# runs past the scan timeout.
_SCAN_MAX_TOKENS = 900


def _normalized(text: str) -> str:
    return " ".join((text or "").casefold().split())


def _copied_from_source(bullet: str, source: str) -> bool:
    """Reject pasted sentences. A real rewrite will not be a long source substring."""
    cleaned = _normalized(bullet)
    passage = _normalized(source)
    return len(cleaned) >= 40 and cleaned in passage


def summarize_scan(drug_name: str, passages: list[str], tier: str, specialty: str) -> tuple[list[str], str]:
    """Rewrite each selected passage into 3–4 clinician-readable sentences.

    Passage order is preserved, and bullets from each passage stay together.
    No patient identifiers or chart fields belong in this request. Failed model
    calls are not cached. If Grok does not return a valid rewrite, the caller
    gets an empty list rather than the original label text.
    """
    sources = tuple(text.strip() for text in passages[:3] if text.strip())
    if settings.llm_enabled and sources and sum(map(len, sources)) <= 120_000:
        try:
            bullets = _cached_scan_bullets(
                _SCAN_PROMPT_VERSION, drug_name, sources, tier, specialty,
                settings.llm_model, settings.llm_api_base,
            )
            return list(bullets), "grok"
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
            pass
    # Never ship label text. If Grok did not rewrite it, the HUD stays empty.
    return [], "unavailable"


@lru_cache(maxsize=128)
def _cached_scan_bullets(prompt_version: str, drug_name: str, sources: tuple[str, ...],
                         tier: str, specialty: str, model: str, api_base: str) -> tuple[str, ...]:
    # Cache only validated successes. Source text, tier, specialty and provider
    # all participate in the key, so a repeat scan cannot reuse the wrong tier.
    del prompt_version
    least, most = _BULLETS_PER_PASSAGE
    schema = {
        "type": "object", "additionalProperties": False,
        "properties": {"sections": {
            "type": "array",
            "minItems": len(sources), "maxItems": len(sources),
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"bullets": {
                    "type": "array", "items": {"type": "string"},
                    "minItems": least, "maxItems": most,
                }},
                "required": ["bullets"],
            },
        }},
        "required": ["sections"],
    }
    response = requests.post(
        f"{api_base.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": (
                    "Rewrite each passage into 3 or 4 sentences a clinician can read. "
                    "Use 3 when the passage is thin and 4 when it has several distinct facts. "
                    "One important fact per sentence, at most 28 words. "
                    "Keep warnings, contraindications, who it is for, dose, duration, boxed warnings, and stop-use rules. "
                    "Do not quote the label."
                )},
                {"role": "user", "content": json.dumps({
                    "drug": drug_name, "specialty": specialty, "familiarity": tier,
                    "passages": list(sources),
                    "task": "Rewrite each passage, in order, into 3 or 4 original sentences. One fact each. Do not paste the label.",
                })},
            ],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "scan_summary", "strict": True, "schema": schema,
            }},
            # Default reasoning on grok-4.7 runs past the scan timeout.
            "reasoning_effort": "low",
            "max_tokens": _SCAN_MAX_TOKENS,
            "temperature": 0.2,
        },
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    choice = response.json()["choices"][0]
    if choice.get("finish_reason") != "stop":
        raise ValueError("Incomplete scan summary")
    payload = json.loads(choice["message"]["content"])
    if not isinstance(payload, dict) or set(payload) != {"sections"}:
        raise ValueError("Invalid scan summary shape")
    sections = payload["sections"]
    if not isinstance(sections, list) or len(sections) != len(sources):
        raise ValueError("Missing source summaries")
    cleaned = []
    for section, source in zip(sections, sources):
        if not isinstance(section, dict) or set(section) != {"bullets"}:
            raise ValueError("Invalid section")
        bullets = section["bullets"]
        if not isinstance(bullets, list) or not least <= len(bullets) <= most:
            raise ValueError("Wrong bullet count")
        for bullet in bullets:
            if not isinstance(bullet, str):
                raise ValueError("Invalid bullet")
            bullet = " ".join(bullet.split())
            if not bullet or len(bullet) > _MAX_BULLET_CHARS or len(bullet.split()) > _MAX_BULLET_WORDS:
                raise ValueError("Bullet exceeds card bounds")
            if _copied_from_source(bullet, source):
                raise ValueError("Bullet copied source text")
            cleaned.append(bullet)
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("Repeated summary bullets")
    return tuple(cleaned)


def generate_answer(
    query: str,
    context: list[str],
    tier: str = "new",
    specialty: str | None = None,
    patient_context: str | None = None,
) -> str:
    """
    Generate a spoken-ready answer to `query`, grounded only in `context`.

    This is the single LLM swap point for the application. Retrieval happens
    before this function is called. `patient_context` is an optional,
    already-formatted block of the currently-selected patient's clinically
    relevant fields (age, sex, weight, allergies, current medications) —
    passed through as plain context, never as an instruction to make a
    clinical judgment.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query cannot be empty")

    if not context:
        return _NOT_COVERED

    # Normalize unexpected tier values rather than allowing them to alter
    # the prompt in an uncontrolled way.
    if tier not in _SENTENCES_BY_TIER:
        tier = "new"

    # Retrieved chunks stay off the wire unless Grok rewrites them.
    if settings.llm_enabled:
        answer = _call_llm(query, context, tier, specialty, patient_context)
        if answer:
            return answer
    return _ASK_UNAVAILABLE


# Spoken answers are a few sentences. Cap completion tokens and keep
# reasoning on low so grok-4.7 does not run past the request timeout.
_ASK_MAX_TOKENS = 500
_ASK_CHUNK_CHARS = 1600
_ASK_CONTEXT_CHARS = 6000


def _bound_ask_context(context: list[str]) -> list[str]:
    """Keep the prompt short enough that a low-effort Grok call can finish."""
    bounded: list[str] = []
    used = 0
    for chunk in context:
        text = " ".join((chunk or "").split())
        if not text:
            continue
        room = _ASK_CONTEXT_CHARS - used
        if room < 80:
            break
        limit = min(_ASK_CHUNK_CHARS, room)
        if len(text) > limit:
            trimmed = text[:limit]
            if " " in trimmed:
                trimmed = trimmed.rsplit(" ", 1)[0]
            text = trimmed
        bounded.append(text)
        used += len(text)
    return bounded


def _call_llm(
    query: str,
    context: list[str],
    tier: str,
    specialty: str | None = None,
    patient_context: str | None = None,
) -> Optional[str]:
    """
    Call the configured xAI-compatible chat-completions endpoint.

    Returns None on any API/network/response-format failure so the caller
    can fall back to a grounded extractive answer.
    """
    sentences = _SENTENCES_BY_TIER.get(tier, 2)
    bounded = _bound_ask_context(context)

    joined = "\n\n".join(
        f"[Source {i + 1}]\n{chunk}"
        for i, chunk in enumerate(bounded)
    )

    system_prompt = _SYSTEM_PROMPT.format(
        sentences=sentences,
        tier=tier,
        specialty=(specialty or "").strip() or "general",
    )

    chart = (patient_context or "").strip()
    patient_block = f"Selected patient chart:\n{chart}\n\n" if chart else ""

    user_prompt = (
        f"{patient_block}"
        "Drug reference context:\n\n"
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
                "reasoning_effort": "low",
                "max_tokens": _ASK_MAX_TOKENS,
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
