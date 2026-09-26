# Drug dossiers

One plain-text file per drug. The filename stem is the `drug_id` used everywhere
else (API responses, `Lens/Lens/Models/DemoDrugCatalog.swift`, and the Create ML
class labels described in `training/README.md`), so renaming a file renames the
drug across the whole system.

## Format

A metadata block, then `##` sections:

```
name: Adderall
barcode: 0363323012345
aliases: adderall xr, amphetamine salts
headline: CNS stimulant · Schedule II

## Basics
Prose paragraphs are what retrieval searches over.
- Lines starting with a dash become HUD bullets.
```

`retrieval/ingest.py::load_dossiers` parses these files, and three things consume
the result:

- `db/seed.py` creates the `drugs` rows (including `barcode`, which `/detect` matches on).
- `routes/drug.py::get_summary` picks which sections to show per familiarity tier.
- `retrieval/ingest.py::ingest_docs` chunks the prose per section for RAG.

## Which sections map to which tier

| Tier | Sections the HUD leads with |
|---|---|
| `new` | Basics, Warnings |
| `returning` | Dosing, Side effects, Warnings |
| `expert` | Trial data, Interactions, Dosing |

Keep every drug's section names identical, and write the sections so the tiers
read as different *depth*, not the same content reworded — that contrast is the
thing a judge is supposed to notice without it being explained.

## Accuracy

This is demo content written from public labeling for a hackathon. It has not
been clinically reviewed and must not be treated as prescribing information.
