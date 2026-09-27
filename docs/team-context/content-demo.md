# Lane context: Content & demo

Read `CLAUDE.md` at the repo root first — this doc only covers what's specific to your lane. This doc has been refreshed against the current codebase (unlike some of the other lane docs, which may still describe the original scaffold — cross-check anything that looks stale).

## What you own

The data and product logic that makes the personalization loop visible and convincing — this is arguably the highest-leverage lane for the pitch, since it's what turns "camera app" into "engagement engine."

- `backend/app/personalization/scorer.py` — `score_familiarity`/`tier_for_touch_count` (the `new`/`returning`/`expert` tier logic) **and** `resolve_specialty`/`specialty_section_keys` (maps a clinician's free-text specialty onto one of ~19 dossier-section groupings — cardiology gets led into interactions/pharmacology, pediatrics into pediatric-use sections, etc.). Both feed `build_summary_content`, which decides what the HUD actually shows.
- `backend/data/drug_docs/*` — ~1,800 real openFDA-derived drug dossiers (SPL/drug-facts field dumps, one file per drug), parsed by `retrieval/ingest.py::parse_dossier`/`parse_dossier_fields`. This is real regulatory text, not mock content.
- `backend/app/db/seed.py` — demo HCPs (`DEMO_HCPS`, IDs matching `HCP.demoProfiles` in `Lens/Lens/Models/HCP.swift`) and the drug catalog, seeded idempotently on every backend startup. Demo account emails follow `firstname.lastname@lens.demo`, password `demo`.
- The demo script itself (not a code file — see below).

## What you depend on (don't break, coordinate before changing)

- `backend/app/db/database.py` / Mongo collections (Backend & data lane) — `score_familiarity` reads engagement touch counts from Mongo, not a SQL table. If the collection/field names change, your scoring logic needs to follow.
- `backend/app/retrieval/ingest.py` (Voice & LLM lane) — your `drug_docs/` files are only useful once ingestion chunks and indexes them; the current parser expects either a raw SPL/drug-facts field dump (`field_name:\n  text...`) or markdown-style section headers. Coordinate before introducing a third format.
- `backend/app/routes/drug.py::get_summary` (Backend & data lane) — reads tier + specialty from your scorer to decide which dossier sections to surface, and applies `personalization/patient_check.py`'s name-based chart flags on top.

## Current state

The personalization logic, real dossier corpus, and demo seed data are all built and running — this isn't a from-scratch build task anymore, it's tuning. The demo now spans three surfaces (iOS app, web dashboard, backend) that all read the same seeded HCPs/drugs, so a demo script needs to account for all three if the pitch shows more than the phone.

## Pitfalls specific to this lane

- **Tune thresholds against the demo script, not in the abstract.** Tier boundaries are `RETURNING_AT = 1`, `EXPERT_AT = 2` touches in `scorer.py` — if you change these, make sure the demo script's scan count still lands on the tier change you want to show live.
- **Specialty lens sections must exist in the actual dossier**, or the fallback is generic tier content — `_SPECIALTY_FIELDS` in `scorer.py` lists which SPL/drug-facts field names each specialty prefers; adding a new specialty means picking field names that are actually present across your seeded drugs, not just plausible-sounding ones.
- **Write/curate dossiers so the tiers are obviously different**, not just longer. A judge should be able to glance at the `new` vs `expert` HUD content and immediately see it's a different depth of information.
- Don't invent patient-level personalization of the tier itself, or additional tiers beyond `new`/`returning`/`expert` — that's explicitly out of scope (see `CLAUDE.md`). Patient context is a separate, additive thing threaded through the LLM answer only (Voice & LLM lane), not a scoring input.

## Definition of done for the hackathon

A judge watches the same HCP persona scan the same drug twice and can immediately see — without anything being explained to them — that the second scan looks more advanced than the first, that the content shown differs meaningfully by the HCP's specialty, and that a follow-up voice question gets an answer pulled from real dossier content, not generic knowledge.
