# Lane context: Voice & LLM

Read `CLAUDE.md` at the repo root first — this doc only covers what's specific to your lane.

## What you own

Turning a spoken follow-up question into a grounded, spoken answer.

- `Lens/Lens/Voice/SpeechRecognizer.swift` — mic → transcribed text (`SFSpeechRecognizer`)
- `Lens/Lens/Voice/SpeechSynthesizer.swift` — text → spoken audio (`AVSpeechSynthesizer`)
- `backend/app/retrieval/index.py` — `retrieve(drug_id, query)`, the **only** entry point the rest of the app uses for retrieval (see `CLAUDE.md`'s "swap points")
- `backend/app/retrieval/embed.py` — embedding wrapper
- `backend/app/llm/client.py` — `generate_answer(query, context)`, the **only** entry point for LLM calls
- The `ask_question` half of `backend/app/routes/drug.py` (the `get_summary` half belongs to Backend & data)

## What you depend on (don't break, coordinate before changing)

- `backend/app/retrieval/ingest.py` (Backend & data lane) — builds the in-memory structure your `retrieve()` reads. Agree on the shape of what `ingest_docs()` returns/stores before both sides implement in parallel.
- `backend/data/drug_docs/*` (Content & demo lane) — the actual dossier content you're retrieving from. You need real files here early to test retrieval meaningfully, not lorem ipsum.
- `Lens/Lens/Networking/APIClient.swift::askQuestion` — the iOS-side caller; response shape is `{answer_text: string}`.

## Suggested build order

1. Get `embed.py::embed_text` working against a real sentence-transformers model, loaded once at module import (not per-call — that's slow).
2. Get `ingest.py` + `index.py::retrieve` working against a couple of real files in `backend/data/drug_docs/`, tested directly (a quick script or a pytest, not through the API yet).
3. Wire `llm/client.py::generate_answer` against the sponsor's LLM API with a system prompt that forces grounding in the passed `context` — this is what keeps answers from hallucinating dosing info, which matters for a pharma-facing demo.
4. Wire `routes/drug.py::ask_question` to call `retrieve()` then `generate_answer()` in sequence.
5. iOS: `SpeechRecognizer` → `APIClient.askQuestion` → `SpeechSynthesizer.speak`, only once the backend round trip works via `curl`/Postman first.

## Pitfalls specific to this lane

- **Do not let any other file call `embed_text` or the LLM API directly.** That's the entire point of `index.py`/`client.py` being the swap points — if `routes/drug.py` or anything else bypasses them, the upgrade path in `docs/architecture.md` breaks.
- **Keep LLM answers short.** They get spoken aloud via `AVSpeechSynthesizer` — a paragraph-long answer is a bad demo moment. Constrain this in the system prompt, not with client-side truncation (truncation can cut off mid-sentence).
- **Retrieval should filter by `drug_id` first, then rank by similarity within that drug** — don't let a query about Drug A pull in chunks from Drug B's dossier just because they're semantically close.
- **On-device speech recognition requires explicit authorization** (`SFSpeechRecognizer.requestAuthorization`) separate from microphone permission — request both, and don't assume one implies the other.

## Definition of done for the hackathon

Ask a real follow-up question out loud about a real seeded drug, get a spoken answer back that's actually grounded in that drug's doc content (not generic LLM knowledge) — and get a visibly different, more detailed answer when the HCP's familiarity tier is `expert` vs. `new`.
