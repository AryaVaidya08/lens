# Lane context: Content & demo

Read `CLAUDE.md` at the repo root first — this doc only covers what's specific to your lane.

## What you own

The data and product logic that makes the personalization loop visible and convincing — this is arguably the highest-leverage lane for the pitch, since it's what turns "camera app" into "engagement engine."

- `backend/app/personalization/scorer.py::score_familiarity` — the tier logic (`new` / `returning` / `expert`)
- `backend/data/drug_docs/*` — the actual drug reference documents that get ingested and retrieved from
- `backend/app/db/seed.py` — mock HCPs, mock drugs, and pre-existing engagement state for the demo
- The demo script itself (not a code file — see below)

## What you depend on (don't break, coordinate before changing)

- `backend/app/db/models.py` (Backend & data lane) — `Engagement.touch_count` is what `score_familiarity` reads. If the schema changes, your scoring logic needs to follow.
- `backend/app/retrieval/ingest.py` (Voice & LLM lane) — your `drug_docs/` files are only useful once ingestion actually chunks and indexes them; coordinate on file format (plain text vs. markdown vs. structured sections) early so ingestion doesn't have to be rewritten around your content.
- `backend/app/routes/drug.py::get_summary` (Backend & data lane) — reads the tier from your scorer to decide which fields of a drug's data to surface.

## Suggested build order

1. Pick 3-4 real (or realistic mock) drugs and write a short dossier per drug in `backend/data/drug_docs/` — basics (what it treats, standard dosing) plus more advanced content (trial data, edge-case dosing, interactions) that only an "expert"-tier view should lead with.
2. Implement `score_familiarity` with simple thresholds (e.g. 0 touches → `new`, 1-2 → `returning`, 3+ → `expert`) — keep it readable, this is the file most likely to get pulled up live during the pitch.
3. Seed 3-4 mock HCPs in `seed.py`, with at least one HCP pre-seeded with engagement history against one drug — so the demo can show the "second scan" tier jump without needing two live scans of the same drug in front of judges.
4. Write the actual demo script: which HCP persona, which drug, in what order, so the tier change and the voice follow-up both land inside your demo time limit.

## Pitfalls specific to this lane

- **Tune thresholds against the demo script, not in the abstract.** If your demo only has time for two scans of the same drug, the tier needs to visibly change between scan 1 and scan 2 — don't pick thresholds that require three touches if you only have time to demo two.
- **Write dossiers so the tiers are obviously different**, not just longer. A judge should be able to glance at the `new` vs `expert` HUD content and immediately see it's a different depth of information, not the same paragraph with more words.
- **Keep dossier files simple** (plain text or lightly structured markdown) unless you've confirmed with the Voice & LLM lane that `ingest.py` handles something fancier — an elaborate doc format that ingestion can't parse is wasted work.
- Don't invent patient-level personalization or additional tiers beyond `new`/`returning`/`expert` — that's explicitly out of scope (see `CLAUDE.md`).

## Definition of done for the hackathon

A judge watches the same HCP persona scan the same drug twice and can immediately see — without anything being explained to them — that the second scan looks more advanced than the first, and a follow-up voice question gets an answer pulled from your actual dossier content, not generic knowledge.
