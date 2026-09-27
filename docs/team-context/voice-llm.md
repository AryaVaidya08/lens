# Lane context: Voice & LLM

Read `CLAUDE.md` at the repo root first — this doc only covers what's specific to your lane. This doc has been refreshed against the current codebase (unlike some of the other lane docs, which may still describe the original scaffold — cross-check anything that looks stale).

## What you own

Turning a spoken follow-up question into a grounded, spoken answer, personalized by tier, specialty, and (optionally) the selected patient.

- `Lens/Lens/Voice/SpeechRecognizer.swift` (+ `SpeechRecognitionDriver.swift`, `AppleSpeechRecognitionDriver.swift`) — mic → transcribed text (`SFSpeechRecognizer`)
- `Lens/Lens/Voice/SpeechSynthesizer.swift` (+ `SpeechVoiceSelection.swift`, `InstalledSpeechVoices.swift`) — text → spoken audio (`AVSpeechSynthesizer`)
- `Lens/Lens/Voice/VoiceAssistantSession.swift` — wires recognizer → `APIClient.askQuestion` → synthesizer; the `answerProvider` closure defaults to `backendAnswer` and falls back to a local demo reply if the backend isn't reachable (`Lens/Lens/Voice/PlaceholderAssistant.swift`), so voice input never dead-ends in a demo.
- `Lens/Lens/Views/VoiceAssistantView.swift` — the voice UI surface.
- `backend/app/retrieval/index.py::retrieve(drug_id, query, top_k=None, specialty=None)` — the **only** entry point the rest of the app uses for retrieval (see `CLAUDE.md`'s "swap points"). Filters by `drug_id` first, then ranks by cosine similarity plus a section-name-match bonus and a specialty-lens bonus.
- `backend/app/retrieval/embed.py` — `embed_text`/`embed_texts` via `sentence-transformers` (`all-MiniLM-L6-v2` by default), with a deterministic lexical-hash fallback (`using_model()` reports which is active) so the app still runs with no model downloaded.
- `backend/app/llm/client.py::generate_answer(query, context, tier="new", specialty=None, patient_context=None)` — the **only** entry point for LLM calls, against xAI's Grok API. Falls back to a grounded extractive answer (built directly from `context`, no external call) when no API key is configured.
- The `ask` route in `backend/app/routes/drug.py` (the `summary` route in the same file belongs to Backend & data).

## What you depend on (don't break, coordinate before changing)

- `backend/app/retrieval/ingest.py` (Backend & data lane) — parses `backend/data/drug_docs/*` (openFDA SPL/drug-facts field dumps, ~1,800 files) into `Dossier` objects and chunks, and caches embeddings to `data/.embedding_cache.npz` so startup doesn't re-embed everything every reload.
- `backend/app/personalization/scorer.py` (Content & demo lane) — supplies the `tier` and resolved `specialty` that `retrieve()` and `generate_answer()` take as parameters. You don't compute these yourself.
- `Lens/Lens/Networking/APIClient.swift::askQuestion` / `frontend/src/api.js` — the callers; response is the answer text plus whatever conversation/history shape `routes/drug.py` and `routes/profile.py::chats` define.

## Current state

Retrieval, embedding, and LLM generation are all implemented and running against real dossier content, not lorem ipsum — this is real RAG over real openFDA-derived text, not a stub. The `generate_answer` extractive fallback exists specifically so the demo never goes fully dark if the LLM API is rate-limited or the key is missing; know which mode is active via `GET /status`.

## Pitfalls specific to this lane

- **Do not let any other file call `embed_text`/`embed_texts` or the LLM API directly.** That's the entire point of `index.py`/`client.py` being the swap points — if `routes/drug.py` or anything else bypasses them, the upgrade path in `docs/architecture.md` breaks.
- **Keep LLM answers short.** They get spoken aloud via `AVSpeechSynthesizer` — a paragraph-long answer is a bad demo moment. Constrain this in the system prompt, not with client-side truncation (truncation can cut off mid-sentence).
- **Retrieval filters by `drug_id` first, then ranks by similarity within that drug** — don't let a query about Drug A pull in chunks from Drug B's dossier just because they're semantically close.
- **`patient_context` is plain context, never an instruction.** If a patient is selected for the scan, their age/sex/weight/allergies/meds get passed into `generate_answer` as a formatted block so follow-up questions can reference them — this must never be phrased as "decide whether this is safe for this patient," since that's explicitly out of scope (see `personalization/patient_check.py`, which does its own separate name-matching, not the LLM).
- **On-device speech recognition requires explicit authorization** (`SFSpeechRecognizer.requestAuthorization`) separate from microphone permission — request both, don't assume one implies the other.

## Definition of done for the hackathon

Ask a real follow-up question out loud about a real drug, get a spoken answer back that's actually grounded in that drug's dossier content (not generic LLM knowledge), get a visibly different, more detailed answer when the HCP's familiarity tier is `expert` vs. `new`, get a different section emphasis depending on the HCP's specialty, and — with a patient selected — get an answer that references that patient's context without making a clinical call.
