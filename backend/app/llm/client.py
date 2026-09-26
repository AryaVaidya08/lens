"""
The LLM swap point.

Wraps whichever LLM API is used (sponsor API for the hackathon).
Nothing else in the codebase should call the LLM API directly — see
docs/architecture.md's scaling table for why this stays isolated.

Owned by: Voice & LLM lane.
"""


def generate_answer(query: str, context: list[str]) -> str:
    """
    Generates a spoken-ready answer to `query`, grounded in `context`
    (the chunks returned by retrieval/index.py::retrieve).

    TODO: implement — call the sponsor LLM API using app.config.settings
    for the API key, with a system prompt that instructs it to answer
    only from `context` and to keep the answer short enough to speak
    aloud via AVSpeechSynthesizer.
    """
    # TODO: implement
    raise NotImplementedError
