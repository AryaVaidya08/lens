"""
Shared text tokenization.

Used by retrieval/embed.py (to build vectors) and llm/client.py (to rank
sentences for the offline answer). Both need to agree that "what is the usual
dose" is about "usual dose" — if only one of them strips stopwords, retrieval
and answer selection disagree and the spoken answer stops matching the question.
"""

import re

_TOKEN = re.compile(r"[a-z0-9]+")

STOPWORDS = frozenset(
    """a about all also an and any are as at be been being but by can could did do does
    doing else ever for from give got had has have here how i if in into is it its just
    know let like may me might much must my need now of on only or other our out over
    please really see should so some such sure tell than that the their them then there
    these they thing this to use used very want was way well were what when where which
    who why will with would you your""".split()
)


# Deliberately crude suffix folding, not a real stemmer. It exists so lexical
# matching treats "dose", "doses", and "dosing" as the same term, which is the
# difference between a dosing question retrieving the Dosing section and
# retrieving whichever section happens to repeat the word "dose" most often.
# Real embeddings handle this on their own; this only backs the offline path.
_SUFFIXES = ("ions", "ion", "ing", "ies", "ed", "es", "s", "ly")


def _fold(token: str) -> str:
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)]
            break
    if len(token) > 3 and token.endswith("e"):
        token = token[:-1]
    return token


def content_terms(text: str) -> list[str]:
    """Lowercased, suffix-folded tokens with stopwords and short noise removed."""
    return [
        _fold(token)
        for token in _TOKEN.findall(text.lower())
        if len(token) > 2 and token not in STOPWORDS
    ]
