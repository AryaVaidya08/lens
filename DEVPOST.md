## Inspiration

Pharma engagement is almost always push (a rep message or in-app notification that gets ignored) or pull (a physician has to decide to search for something). We wanted a third mode: the physical drug sample already sitting in a clinician's hand becomes the trigger. No search intent required — the interaction starts the moment they pick the object up.

## What it does

Lens is a spatial HCP copilot: point a phone at a physical drug sample and get a personalized, patient-aware, voice-interactive clinical HUD anchored to that object in AR.

**Detection pipeline (on-device, three stages, in order):**
1. A Create ML–trained object detector (`PillBottleDetector`, run via `VNCoreMLRequest`) finds the bottle in frame and returns a bounding box, filtering out detections below a confidence threshold so the HUD doesn't jitter on false positives.
2. Vision's barcode reader is tried first against that region for an exact drug ID.
3. If no barcode resolves, on-device OCR reads the label text and the backend's `/detect` endpoint resolves it against the drug catalog.

**The personalization loop (the core mechanic):** every HCP–drug pair has a `touch_count` in MongoDB. `personalization/scorer.py` maps that count directly to a tier — 0 touches → `new`, 1 → `returning`, 2+ → `expert` — computed *before* the current scan is logged, so the HUD reflects prior history, not the scan in progress. Each tier has its own priority list of openFDA dossier fields: `new` leads with `indications_and_usage`/`purpose`/`description`; `returning` moves to `dosage_and_administration`/`warnings`; `expert` jumps to `drug_interactions`, `clinical_pharmacology`, `mechanism_of_action`. Scan the same drug three times as the same HCP and the headline changes from "What it is" → "Dosing & precautions" → "Clinical profile," pulling from different sections of the same 1,822-document openFDA corpus each time.

On top of tier, the HCP's registered specialty reshapes retrieval and the HUD through a specialty lens. We built 19 lenses (primary care, cardiology, endocrinology, pediatrics, oncology, psychiatry, nephrology, etc.), each pointing at 3 dossier fields most relevant to that practice — a cardiologist scanning the same drug as a pediatrician sees different sections surfaced, even at the same familiarity tier. ~80 raw specialty strings (e.g. "interventional cardiology," "pediatric endocrinology," "hospice and palliative medicine") normalize down to those 19 lenses via an alias table, and boxed-warning/contraindication content is always reserved a slot regardless of specialty so safety information is never edited out for relevance.

**Patient context, kept separate from personalization:** when an HCP has a patient selected, `personalization/patient_check.py` does a token-overlap match between the patient's recorded allergies/current medications and the scanned drug's `contraindications`/`drug_interactions`/`warnings` fields — surfaced as a chart-check flag on the HUD, explicitly not a clinical decision or interaction checker. Separately, that patient's age/sex/weight/allergies/medications are passed as plain-text context into the LLM prompt (`llm/client.py::generate_answer`'s `patient_context` param) so voice follow-ups can be answered with that specific patient in mind. Neither of these touches the familiarity tier — tier scoring stays HCP-level by design, so the personalization signal never gets diluted by which patient happens to be selected during a given scan.

**Grounded voice Q&A:** questions are answered by `retrieval/index.py::retrieve()`, the single retrieval entry point in the codebase — no other file is allowed to touch embeddings or a vector store directly. It embeds the query with `sentence-transformers/all-MiniLM-L6-v2`, restricts candidates to the scanned drug's own chunks (so a question can never leak context from another drug), ranks by cosine similarity, and adds a +0.2 bonus when the query's terms match a chunk's section name (so "what's the boxed warning" reliably lands on the boxed-warning section instead of whatever section happens to repeat "warning" most) plus a smaller +0.05 bonus for chunks matching the HCP's specialty lens. The top 4 chunks go to `llm/client.py::generate_answer()` — the single LLM call site in the codebase — which prompts xAI's Grok with a system prompt that scales answer length by tier (2 sentences for `new`, 3 for `returning`, 4 for `expert`), forbids inventing dosing or trial data, and constrains output to plain prose because the response is read aloud via `AVSpeechSynthesizer`.

**Web workspace:** a React 19 + Vite dashboard hits the same 23-endpoint FastAPI backend, giving a clinician chat history, patient records, and a medication-review workflow that OCRs a bottle label and diffs it against the patient's recorded medication list using the same overlap logic as the chart check — without inventing substitutions.

## How we built it

- **iOS:** SwiftUI, ARKit, Vision, Create ML/Core ML, Speech, AVSpeechSynthesizer.
- **Backend:** FastAPI, PyMongo against real MongoDB (Atlas or local; `mongomock` in tests), `sentence-transformers` for embeddings, xAI Grok for generation.
- **Auth:** PBKDF2-HMAC-SHA256 password hashing at 200,000 iterations in production (dropped to 2,000 only when the test suite is running against `mongomock`), per-password random 16-byte salts, opaque session tokens where only the SHA-256 hash is stored server-side (the raw token is returned once, at login), 14-day session expiry, and a 429 rate limiter on auth attempts. No route trusts a client-supplied `hcp_id` for anything auth-sensitive — every route is scoped to the session the bearer token resolves to.
- **Data:** MongoDB backs HCP profiles, patients, engagement counts, sessions, and chat history. Patient records are scoped per-clinician. Medication reviews use optimistic concurrency — a `revision` field checked on write — so two edits to the same review can't silently clobber each other.
- **Retrieval + generation:** an in-memory index (no hosted vector DB) built at startup from 1,822 openFDA-derived drug dossiers in `backend/data/drug_docs/`, accessed only through `retrieval/index.py::retrieve()`, feeding `llm/client.py::generate_answer()` as the only LLM call site — both are explicit swap points so a hosted vector DB or a different model provider can replace either without touching any caller.
- **Web:** React 19 + Vite, same API contract as iOS.

## Challenges we ran into

- Getting the tier transition to be *visible* in under a minute of demo time — the whole point breaks if a judge can't tell scan 1 from scan 3 without an explanation, which is why tier changes the HUD headline and the dossier section, not just a hidden ranking weight.
- Keeping the specialty lens from overriding safety content: early versions could surface a cardiology-relevant section while starving out a boxed warning, so the scorer now always reserves a slot for `boxed_warning`/`contraindications` regardless of which lens is active.
- Normalizing ~80 raw specialty strings a signup form can produce into a manageable set of lenses without falling back to "generic" for anyone — unmapped specialties resolve to the primary-care lens rather than showing nothing.
- Keeping patient context and familiarity tier from bleeding into each other — it was tempting to let patient data influence retrieval ranking, but that would mean the same HCP gets inconsistent personalization depending on which patient happens to be selected, so patient context stays confined to the LLM prompt and the chart-check flag.
- Making retrieval section-aware without a hosted vector DB: an in-memory cosine-similarity index over ~1,822 documents needed a section-name term-match bonus to reliably answer "what's the boxed warning" instead of drifting to whichever chunk uses the word "warning" most.

## Accomplishments that we're proud of

Three tiers, one touch-count field, and a per-tier dossier field priority list are enough to make the same drug feel like a different, more advanced interaction on the second and third scan — no separate content authored per tier, just different slices of the same openFDA dossier. Pairing that with 19 specialty lenses means the HUD is shaped by *who* is looking and *how many times they've looked*, computed from two pieces of state (`touch_count`, `specialty`) rather than a rules engine.

## What we learned

The personalization signal is cheap to compute (a touch count and a specialty string) but only works if every layer above it — HUD headline, dossier field selection, retrieval ranking, and the LLM's sentence budget — actually reads it. The hard part wasn't building the loop, it was making sure none of the four consumers of tier/specialty silently used their own logic instead.

## What's next for Lens

- NPI-backed clinician verification instead of self-registered specialty.
- A hosted vector database behind the existing `retrieval/index.py::retrieve()` interface — no caller changes needed.
- Real EHR integration so patient context isn't manually entered.
- A larger, continuously updated clinical evidence source beyond the static openFDA snapshot.
- Analytics on how an HCP's tier distribution across their drug list evolves over time.
