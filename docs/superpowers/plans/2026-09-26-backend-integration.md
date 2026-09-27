# Backend Full Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the `drug_data` branch (working RAG retrieval + committed embedding cache) into the `llm-rag` branch (working LLM client + `ask_question` wiring), then implement the still-stubbed DB/personalization/route layer so a full request — detect a drug -> get a personalized summary -> ask a follow-up question -> log engagement -> see the tier change on the next scan — works end-to-end against the real ~1800-drug corpus, with no iOS app required to verify it.

**Architecture:** SQLite (SQLAlchemy) holds HCP/Drug/Engagement rows. `personalization/scorer.py` reads `Engagement.touch_count` to compute a tier and picks which dossier fields to surface for that tier. `routes/*.py` stay thin -- they call `db/`, `personalization/`, `retrieval/`, and `llm/` and shape the HTTP response. The two swap points (`retrieval/index.py::retrieve`, `llm/client.py::generate_answer`) are untouched as call boundaries.

**Tech Stack:** FastAPI, SQLAlchemy 2.x ORM (declarative), SQLite, pytest + FastAPI `TestClient`, sentence-transformers (already wired), OpenAI SDK (already wired on `llm-rag`).

**Spec:** `/Users/arya/Desktop/CodeProjects/lens/CLAUDE.md`, `/Users/arya/Desktop/CodeProjects/lens/README.md`, `/Users/arya/Desktop/CodeProjects/lens/docs/team-context/backend-data.md`, `/Users/arya/Desktop/CodeProjects/lens/docs/team-context/voice-llm.md`

## Global Constraints

- No real auth -- the backend trusts whatever `hcp_id` the client sends (CLAUDE.md).
- One SQLite file, one FastAPI service -- no external DB/queue/container (CLAUDE.md).
- `retrieval/index.py::retrieve(drug_id, query)` is the only entry point for retrieval; `llm/client.py::generate_answer(query, context)` is the only entry point for the LLM. No other file calls embeddings or the LLM API directly (CLAUDE.md).
- Route response shapes must match the API contract table in CLAUDE.md/README exactly (field names included).
- `check_same_thread=False` must stay set on the SQLite engine (backend-data.md pitfall).
- Run everything from inside `backend/` -- `app.main` assumes that cwd (backend-data.md).
- Keep `routes/*.py` thin; business logic lives in `db/`, `personalization/`, `retrieval/`, `llm/` (backend-data.md).

## Review Focus

- **Unknown `hcp_id` or `drug_id`** (never scanned/engaged before) -- `/profile/{hcp_id}` and `/drug/{drug_id}/summary` must return a sane "new" default, not a 500 or a KeyError, since the persona picker can send any id.
- **`drug_id` with no doc / not in the RAG index** -- `/drug/{drug_id}/ask` and `/drug/{drug_id}/summary` must fail with a clean 404, not an unhandled exception, since detect can resolve to a drug whose dossier text is missing a field.
- **Repeated `POST /engagement/log` for the same (hcp_id, drug_id)** -- must increment `touch_count`, not create duplicate rows or reset it, since the demo's whole point is a visible tier change across repeated scans.
- **`/detect` with neither a barcode match nor a usable OCR match** -- must return a clear 404, not `None` fields, since a physical device will often mis-scan during the demo.
- **Missing `OPENAI_API_KEY`** -- `/drug/{drug_id}/ask` must return a clean error status (502/500 with a message), not crash the whole process, since the key may not be set on every teammate's machine.

---

## Background: why a merge, not a clean implementation

`drug_data` (already pushed, includes a committed 91MB embedding cache) and `llm-rag` (pushed once, "Implemented LLM and RAG integration") both independently modified the **same stub files** from their common ancestor (`updated tasks`, commit `4b5bdbd9`):

| File | `drug_data` | `llm-rag` |
|---|---|---|
| `backend/app/config.py` | absolute paths via `BACKEND_ROOT`, `embedding_cache_path`, `embedding_model` | `python-dotenv`, `openai_api_key`, `XAI_API_KEY`/`XAI_API_BASE` |
| `backend/app/retrieval/embed.py` | `embed_text` + batched `embed_texts`, `lru_cache`-loaded model | `embed_text` only, no batching, no cache |
| `backend/app/retrieval/ingest.py` | paragraph+line chunking (with a fix for label dumps with no blank lines), on-disk `.npz` embedding cache keyed by content hash | simpler blank-line-only chunking (no cache) |
| `backend/app/retrieval/index.py` | `Chunk` dataclass, `set_index`/`get_index`, cosine similarity | plain `dict` entries, cosine similarity |
| `backend/app/main.py` | `SKIP_INGEST` env var (used by tests) | try/except around `ingest_docs` so missing docs don't crash startup |

`drug_data`'s retrieval side is strictly more capable (real caching -- the whole reason the 91MB cache commit is useful -- plus the label-dump chunking fix), so it wins in every conflict. `llm-rag`'s unique, non-conflicting value is `backend/app/llm/client.py` (a working OpenAI-backed `generate_answer`) and half of `backend/app/routes/drug.py` (`ask_question` fully wired) -- neither of which `drug_data` touched, so they merge in cleanly.

The real drug corpus (1821 flat `.txt` files in `backend/data/drug_docs/`) that the committed cache was generated from was **never committed** -- it only exists as uncommitted/untracked files in the main checkout. `drug_data`'s only commit of `drug_docs/` is the old, discarded nested-folder placeholder set (~18,561 junk files like `FINAL DUMB THING/`). This plan commits the real corpus so the already-committed cache actually matches what's on disk for anyone who clones the branch -- otherwise `ingest_docs()` finds the wrong files, the cache keys miss, and it silently re-embeds the wrong (junk) corpus from scratch.

---

### Task 1: Merge `drug_data` into `llm-rag`, resolve conflicts, restore the real corpus

**Files:**
- Modify: `backend/app/config.py`, `backend/app/main.py`, `backend/app/retrieval/embed.py`, `backend/app/retrieval/index.py`, `backend/app/retrieval/ingest.py`, `backend/requirements.txt`, `.gitignore`
- Replace: `backend/data/drug_docs/` (delete old nested placeholder tree, add the real flat 1821-file corpus + `manifest.json`)

**Interfaces:**
- Produces: `settings.database_url`, `settings.openai_api_key`, `settings.llm_api_key`, `settings.llm_api_base`, `settings.embedding_cache_path`, `settings.embedding_model`, `settings.drug_docs_path` all present on one `Settings` object -- every later task reads these from `app.config.settings`.

- [ ] **Step 1: Create an isolated worktree for this work** (use `EnterWorktree`, name e.g. `backend-integration`)

- [ ] **Step 2: Point the worktree branch at `origin/llm-rag`**

```bash
git fetch origin
git reset --hard origin/llm-rag
```

This is safe only because the worktree branch is brand new with zero unique commits.

- [ ] **Step 3: Merge in `origin/drug_data`**

```bash
git merge origin/drug_data -m "Merge drug_data into llm-rag: reconcile RAG implementations"
```

Expect conflicts in exactly: `backend/app/config.py`, `backend/app/main.py`, `backend/app/retrieval/embed.py`, `backend/app/retrieval/index.py`, `backend/app/retrieval/ingest.py`. `backend/app/llm/client.py` and `backend/app/routes/drug.py` should merge cleanly.

- [ ] **Step 4: Resolve `embed.py`, `index.py`, `ingest.py` -- take `drug_data`'s version verbatim**

```bash
git checkout --ours backend/app/retrieval/embed.py backend/app/retrieval/index.py backend/app/retrieval/ingest.py
git add backend/app/retrieval/embed.py backend/app/retrieval/index.py backend/app/retrieval/ingest.py
```

Verify with `git show HEAD:backend/app/retrieval/ingest.py | grep _split_oversized` before trusting `--ours` vs `--theirs`.

- [ ] **Step 5: Resolve `backend/app/config.py` by hand -- merge both sides**

```python
"""
Central app configuration.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings:
    def __init__(self) -> None:
        self.database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./hcp.db")
        self.llm_api_key: str = os.environ.get("XAI_API_KEY", "")
        self.llm_api_base: str = os.environ.get("XAI_API_BASE", "https://api.x.ai/v1")
        self.openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
        self.drug_docs_path: str = os.environ.get(
            "DRUG_DOCS_PATH",
            str(BACKEND_ROOT / "data" / "drug_docs"),
        )
        self.embedding_cache_path: str = os.environ.get(
            "EMBEDDING_CACHE_PATH",
            str(BACKEND_ROOT / "data" / ".embedding_cache.npz"),
        )
        self.embedding_model: str = os.environ.get(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )


settings = Settings()
```

- [ ] **Step 6: Resolve `backend/app/main.py` by hand -- keep both `SKIP_INGEST` and the missing-docs safety net, wire `init_db`/`seed`**

```python
"""
FastAPI application entrypoint.
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from app.config import settings
from app.routes import detect, drug, engagement, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("SKIP_INGEST") != "1":
        from app.retrieval.ingest import ingest_docs

        try:
            chunks = ingest_docs(settings.drug_docs_path)
            print(f"Loaded {len(chunks)} drug-document chunks.")
        except FileNotFoundError as exc:
            print(f"Drug document ingestion skipped: {exc}")

    from app.db.database import init_db

    init_db()
    from app.db.seed import seed

    seed()

    yield


app = FastAPI(title="HCP Spatial Copilot", lifespan=lifespan)

app.include_router(profile.router)
app.include_router(detect.router)
app.include_router(drug.router)
app.include_router(engagement.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

(`init_db`/`seed` don't exist yet -- Tasks 3-4 add them.)

- [ ] **Step 7: Resolve `requirements.txt`/`.gitignore` -- keep both sides' additions.** Do NOT re-add `backend/data/.embedding_cache.npz`/`.keys.json` to `.gitignore` -- they were deliberately un-ignored and committed on `drug_data`.

- [ ] **Step 8: Commit the merge**

```bash
git add -A
git commit -m "Merge drug_data into llm-rag: keep drug_data's cached retrieval, llm-rag's LLM client"
```

- [ ] **Step 9: Replace the old nested placeholder corpus with the real flat corpus**

```bash
rm -rf backend/data/drug_docs
mkdir -p backend/data/drug_docs
cp /Users/arya/Desktop/CodeProjects/lens/backend/data/drug_docs/*.txt backend/data/drug_docs/
cp /Users/arya/Desktop/CodeProjects/lens/backend/data/manifest.json backend/data/manifest.json
git add backend/data/drug_docs backend/data/manifest.json
```

- [ ] **Step 10: Commit the corpus swap**

```bash
git commit -m "Replace placeholder drug_docs with the real flat FDA-label corpus"
```

- [ ] **Step 11: Verify the committed embedding cache still matches (no re-embed needed)**

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
time .venv/bin/python3 scripts/generate_embeddings.py
```

Expected: completes in a couple of seconds, not ~170s -- if it re-embeds from scratch, the copied files don't byte-match what generated the committed cache.

---

### Task 2: DB engine + session wiring

**Files:** Modify `backend/app/db/database.py`; Test `backend/tests/test_db.py` (new)

**Interfaces:** Produces `Base`, `engine`, `SessionLocal`, `get_db()`, `init_db()`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_db.py
from app.db.database import SessionLocal, init_db, engine
from app.db.models import HCP


def test_init_db_creates_tables():
    init_db()
    db = SessionLocal()
    try:
        db.add(HCP(id="hcp_test", name="Dr. Test", specialty="Cardiology"))
        db.commit()
        found = db.query(HCP).filter(HCP.id == "hcp_test").first()
        assert found is not None
        assert found.name == "Dr. Test"
    finally:
        db.query(HCP).filter(HCP.id == "hcp_test").delete()
        db.commit()
        db.close()
```

- [ ] **Step 2: Run test to verify it fails** -- `cd backend && .venv/bin/python3 -m pytest tests/test_db.py -v` -- expect `ImportError: cannot import name 'init_db'`

- [ ] **Step 3: Implement `backend/app/db/database.py`**

```python
"""
SQLite engine + session setup.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models import Base

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Creates all tables if they don't already exist. Called once at startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit** -- `git add backend/app/db/database.py backend/tests/test_db.py && git commit -m "Implement SQLite engine, session, and init_db"`

---

### Task 3: Finalize SQLAlchemy models

**Files:** Modify `backend/app/db/models.py`

**Interfaces:** Produces `Base`, `HCP(id, name, specialty)`, `Drug(id, name, barcode, generic_name)`, `Engagement(hcp_id, drug_id, touch_count, last_seen)`.

- [ ] **Step 1: Implement `backend/app/db/models.py`**

```python
"""
SQLAlchemy models.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    barcode = Column(String, nullable=True, index=True)
    generic_name = Column(String, nullable=True)


class Engagement(Base):
    __tablename__ = "engagements"

    hcp_id = Column(String, ForeignKey("hcps.id"), primary_key=True)
    drug_id = Column(String, ForeignKey("drugs.id"), primary_key=True)
    touch_count = Column(Integer, nullable=False, default=0)
    last_seen = Column(DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))
```

`Drug.id` is the same string used everywhere as `drug_id` (matches `drug_docs/<id>.txt` filename stems) -- this is what lets `retrieve(drug_id, query)` and `Drug.id` refer to the same thing with no translation table.

- [ ] **Step 2: Run `tests/test_db.py` to confirm nothing broke**

- [ ] **Step 3: Commit** -- `git add backend/app/db/models.py && git commit -m "Finalize HCP/Drug/Engagement models"`

---

### Task 4: Seed demo data

**Files:** Modify `backend/app/db/seed.py`; Test `backend/tests/test_seed.py` (new)

**Interfaces:** Produces `seed()` -- idempotent, called from `main.py`'s `lifespan`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_seed.py
from app.db.database import SessionLocal, init_db
from app.db.seed import seed
from app.db.models import HCP, Drug, Engagement


def test_seed_is_idempotent():
    init_db()
    seed()
    seed()  # calling twice must not duplicate rows or error

    db = SessionLocal()
    try:
        assert db.query(HCP).count() >= 3
        assert db.query(Drug).count() >= 3
        ibuprofen = db.query(Drug).filter(Drug.id == "ibuprofen").first()
        assert ibuprofen is not None
        assert ibuprofen.barcode is not None

        expert_row = db.query(Engagement).filter(Engagement.touch_count >= 3).first()
        assert expert_row is not None, "seed data should include one pre-existing 'expert' engagement for the demo"
    finally:
        db.close()
```

- [ ] **Step 2: Run test to verify it fails** -- expect `NotImplementedError`

- [ ] **Step 3: Implement `backend/app/db/seed.py`**

Demo drugs verified present in `backend/data/drug_docs/`: `ibuprofen.txt`, `advil.txt`, `tylenol.txt`, `acetaminophen.txt`.

```python
"""
Demo data seeding.
"""

from datetime import datetime, timedelta, timezone

from app.db.database import SessionLocal
from app.db.models import Drug, Engagement, HCP

DEMO_HCPS = [
    ("hcp_amara", "Dr. Amara Okafor", "Internal Medicine"),
    ("hcp_ben", "Dr. Ben Whitfield", "Cardiology"),
    ("hcp_priya", "Dr. Priya Nair", "Pediatrics"),
]

DEMO_DRUGS = [
    ("ibuprofen", "Ibuprofen", "3-00000-00171", "Ibuprofen"),
    ("advil", "Advil", "3-05000-16803", "Ibuprofen"),
    ("tylenol", "Tylenol", "3-00045-15467", "Acetaminophen"),
    ("acetaminophen", "Acetaminophen", "3-00000-00172", "Acetaminophen"),
]

DEMO_ENGAGEMENTS = [
    ("hcp_amara", "ibuprofen", 3, timedelta(days=2)),
]


def seed() -> None:
    """Inserts demo HCPs, Drugs, and a couple of Engagement rows. Safe to call more than once."""
    db = SessionLocal()
    try:
        for hcp_id, name, specialty in DEMO_HCPS:
            if db.query(HCP).filter(HCP.id == hcp_id).first() is None:
                db.add(HCP(id=hcp_id, name=name, specialty=specialty))

        for drug_id, name, barcode, generic in DEMO_DRUGS:
            if db.query(Drug).filter(Drug.id == drug_id).first() is None:
                db.add(Drug(id=drug_id, name=name, barcode=barcode, generic_name=generic))

        db.commit()

        for hcp_id, drug_id, touch_count, age in DEMO_ENGAGEMENTS:
            existing = (
                db.query(Engagement)
                .filter(Engagement.hcp_id == hcp_id, Engagement.drug_id == drug_id)
                .first()
            )
            if existing is None:
                db.add(
                    Engagement(
                        hcp_id=hcp_id,
                        drug_id=drug_id,
                        touch_count=touch_count,
                        last_seen=datetime.now(timezone.utc) - age,
                    )
                )
        db.commit()
    finally:
        db.close()
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit** -- `git add backend/app/db/seed.py backend/tests/test_seed.py && git commit -m "Implement demo data seeding"`

---

### Task 5: Familiarity scoring + tier-based summary content

**Files:** Modify `backend/app/personalization/scorer.py`, `backend/app/retrieval/ingest.py` (additive helper only); Test `backend/tests/test_scorer.py` (new)

**Interfaces:** Produces `score_familiarity(hcp_id, drug_id) -> str`, `build_summary_content(drug_id, tier) -> (headline, bullets)`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_scorer.py
from app.db.database import SessionLocal, init_db
from app.db.models import Engagement
from app.personalization.scorer import score_familiarity, build_summary_content


def test_score_familiarity_thresholds():
    init_db()
    db = SessionLocal()
    try:
        db.query(Engagement).filter(
            Engagement.hcp_id == "hcp_score_test", Engagement.drug_id == "ibuprofen"
        ).delete()
        db.commit()

        assert score_familiarity("hcp_score_test", "ibuprofen") == "new"

        db.add(Engagement(hcp_id="hcp_score_test", drug_id="ibuprofen", touch_count=1))
        db.commit()
        assert score_familiarity("hcp_score_test", "ibuprofen") == "returning"

        db.query(Engagement).filter(
            Engagement.hcp_id == "hcp_score_test", Engagement.drug_id == "ibuprofen"
        ).update({"touch_count": 3})
        db.commit()
        assert score_familiarity("hcp_score_test", "ibuprofen") == "expert"
    finally:
        db.query(Engagement).filter(
            Engagement.hcp_id == "hcp_score_test", Engagement.drug_id == "ibuprofen"
        ).delete()
        db.commit()
        db.close()


def test_build_summary_content_differs_by_tier():
    new_headline, new_bullets = build_summary_content("ibuprofen", "new")
    expert_headline, expert_bullets = build_summary_content("ibuprofen", "expert")

    assert new_bullets != expert_bullets
    assert len(new_bullets) > 0
    assert len(expert_bullets) > 0
    assert isinstance(new_headline, str) and new_headline
```

- [ ] **Step 2: Run tests to verify they fail** -- expect `NotImplementedError`/`ImportError`

- [ ] **Step 3: Add a dossier-field parser to `backend/app/retrieval/ingest.py`** (additive -- do not touch existing `chunk_text`/`_split_paragraphs`/`ingest_docs`)

```python
import re

_FIELD_HEADER = re.compile(r"^[a-z0-9_]+:$")


def parse_dossier_fields(drug_id: str, folder_path: str | None = None) -> dict[str, str]:
    """
    Reads the raw drug_docs file for `drug_id` and returns {field_name: value}.

    The corpus format is one field per block: an unindented "field_name:"
    line followed by one or more indented lines holding that field's text.
    Returns {} if the file can't be found.
    """
    root = Path(folder_path or settings.drug_docs_path)
    for drug_id_found, path in _iter_doc_files(root):
        if drug_id_found != drug_id:
            continue
        fields: dict[str, str] = {}
        current_key: str | None = None
        current_value: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith((" ", "\t")) and _FIELD_HEADER.match(line.strip()):
                if current_key is not None:
                    fields[current_key] = " ".join(current_value).strip()
                current_key = line.strip().rstrip(":")
                current_value = []
            elif current_key is not None and line.strip():
                current_value.append(line.strip())
        if current_key is not None:
            fields[current_key] = " ".join(current_value).strip()
        return fields
    return {}
```

- [ ] **Step 4: Implement `backend/app/personalization/scorer.py`**

```python
"""
Familiarity scoring.
"""

from app.db.database import SessionLocal
from app.db.models import Engagement
from app.retrieval.ingest import parse_dossier_fields

_TIER_FIELD_PRIORITY: dict[str, list[str]] = {
    "new": ["indications_and_usage", "purpose", "description"],
    "returning": [
        "dosage_and_administration",
        "directions",
        "warnings",
        "warnings_and_cautions",
        "precautions",
    ],
    "expert": [
        "drug_interactions",
        "adverse_reactions",
        "clinical_pharmacology",
        "clinical_studies",
        "mechanism_of_action",
        "nonclinical_toxicology",
    ],
}

_TIER_HEADLINES = {
    "new": "What it is",
    "returning": "Dosing & precautions",
    "expert": "Clinical profile",
}

_MAX_BULLET_CHARS = 220


def score_familiarity(hcp_id: str, drug_id: str) -> str:
    """0 -> new, 1-2 -> returning, 3+ -> expert."""
    db = SessionLocal()
    try:
        row = (
            db.query(Engagement)
            .filter(Engagement.hcp_id == hcp_id, Engagement.drug_id == drug_id)
            .first()
        )
        touch_count = row.touch_count if row else 0
    finally:
        db.close()

    if touch_count >= 3:
        return "expert"
    if touch_count >= 1:
        return "returning"
    return "new"


def _truncate(text: str, max_chars: int = _MAX_BULLET_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > max_chars * 0.6:
        cut = cut[:last_space]
    return cut.rstrip(".,; ") + "..."


def build_summary_content(drug_id: str, tier: str) -> tuple[str, list[str]]:
    """Picks which dossier fields to surface for `tier`, returns (headline, bullets)."""
    fields = parse_dossier_fields(drug_id)
    headline = _TIER_HEADLINES.get(tier, "Overview")

    bullets: list[str] = []
    for field_name in _TIER_FIELD_PRIORITY.get(tier, []):
        value = fields.get(field_name)
        if value:
            bullets.append(_truncate(value))
        if len(bullets) >= 3:
            break

    if not bullets:
        bullets = ["No additional information available for this drug yet."]

    return headline, bullets
```

- [ ] **Step 5: Run tests to verify they pass**

- [ ] **Step 6: Commit** -- `git add backend/app/personalization/scorer.py backend/app/retrieval/ingest.py backend/tests/test_scorer.py && git commit -m "Implement familiarity scoring and tier-based summary content"`

---

### Task 6: `POST /detect`

**Files:** Modify `backend/app/routes/detect.py`; Test `backend/tests/test_detect.py` (new)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_detect.py
import pytest
from fastapi.testclient import TestClient

from app.db.database import init_db
from app.db.seed import seed
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_detect_by_barcode():
    resp = client.post("/detect", json={"barcode": "3-00000-00171", "ocr_text": None})
    assert resp.status_code == 200
    body = resp.json()
    assert body["drug_id"] == "ibuprofen"
    assert body["name"] == "Ibuprofen"


def test_detect_by_ocr_fuzzy_match():
    resp = client.post("/detect", json={"barcode": None, "ocr_text": "TYLENOL Extra Strength"})
    assert resp.status_code == 200
    assert resp.json()["drug_id"] == "tylenol"


def test_detect_no_match_returns_404():
    resp = client.post("/detect", json={"barcode": "0000000000", "ocr_text": "not a real drug at all"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail** -- expect `NotImplementedError`

- [ ] **Step 3: Implement `backend/app/routes/detect.py`**

```python
"""
Drug detection resolution endpoint.
"""

from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Drug

router = APIRouter(prefix="/detect", tags=["detect"])

_FUZZY_MATCH_THRESHOLD = 0.5


def _best_name_match(ocr_text: str, drugs: list[Drug]) -> Drug | None:
    needle = ocr_text.lower()
    best: tuple[float, Drug] | None = None
    for drug in drugs:
        score = SequenceMatcher(None, needle, drug.name.lower()).ratio()
        if needle in drug.name.lower() or drug.name.lower() in needle:
            score = max(score, 0.9)
        if best is None or score > best[0]:
            best = (score, drug)
    if best and best[0] >= _FUZZY_MATCH_THRESHOLD:
        return best[1]
    return None


@router.post("")
def detect_drug(payload: dict, db: Session = Depends(get_db)) -> dict:
    """
    Contract:
      <- { "barcode": str | None, "ocr_text": str | None }
      -> { "drug_id": str, "name": str }
    """
    barcode = payload.get("barcode")
    ocr_text = payload.get("ocr_text")

    if barcode:
        drug = db.query(Drug).filter(Drug.barcode == barcode).first()
        if drug:
            return {"drug_id": drug.id, "name": drug.name}

    if ocr_text and ocr_text.strip():
        match = _best_name_match(ocr_text, db.query(Drug).all())
        if match:
            return {"drug_id": match.id, "name": match.name}

    raise HTTPException(status_code=404, detail="Could not resolve a drug from the given barcode/OCR text.")
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit** -- `git add backend/app/routes/detect.py backend/tests/test_detect.py && git commit -m "Implement POST /detect with barcode + fuzzy OCR fallback"`

---

### Task 7: `POST /engagement/log`

**Files:** Modify `backend/app/routes/engagement.py`; Test `backend/tests/test_engagement.py` (new)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_engagement.py
import pytest
from fastapi.testclient import TestClient

from app.db.database import init_db
from app.db.seed import seed
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_log_engagement_increments_touch_count():
    resp1 = client.post("/engagement/log", json={"hcp_id": "hcp_priya", "drug_id": "tylenol"})
    assert resp1.status_code == 200
    count1 = resp1.json()["touch_count"]

    resp2 = client.post("/engagement/log", json={"hcp_id": "hcp_priya", "drug_id": "tylenol"})
    assert resp2.json()["touch_count"] == count1 + 1
```

- [ ] **Step 2: Run test to verify it fails** -- expect `NotImplementedError`

- [ ] **Step 3: Implement `backend/app/routes/engagement.py`**

```python
"""
Engagement logging endpoint.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Drug, Engagement, HCP

router = APIRouter(prefix="/engagement", tags=["engagement"])


@router.post("/log")
def log_engagement(payload: dict, db: Session = Depends(get_db)) -> dict:
    """
    Contract:
      <- { "hcp_id": str, "drug_id": str }
      -> { "touch_count": int }
    """
    hcp_id = payload.get("hcp_id")
    drug_id = payload.get("drug_id")
    if not hcp_id or not drug_id:
        raise HTTPException(status_code=400, detail="hcp_id and drug_id are required")

    if db.query(HCP).filter(HCP.id == hcp_id).first() is None:
        raise HTTPException(status_code=404, detail=f"Unknown hcp_id: {hcp_id}")
    if db.query(Drug).filter(Drug.id == drug_id).first() is None:
        raise HTTPException(status_code=404, detail=f"Unknown drug_id: {drug_id}")

    row = (
        db.query(Engagement)
        .filter(Engagement.hcp_id == hcp_id, Engagement.drug_id == drug_id)
        .first()
    )
    if row is None:
        row = Engagement(hcp_id=hcp_id, drug_id=drug_id, touch_count=0)
        db.add(row)

    row.touch_count += 1
    row.last_seen = datetime.now(timezone.utc)
    db.commit()

    return {"touch_count": row.touch_count}
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit** -- `git add backend/app/routes/engagement.py backend/tests/test_engagement.py && git commit -m "Implement POST /engagement/log as an upsert"`

---

### Task 8: `GET /profile/{hcp_id}`

**Files:** Modify `backend/app/routes/profile.py`; Test `backend/tests/test_profile.py` (new)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_profile.py
import pytest
from fastapi.testclient import TestClient

from app.db.database import init_db
from app.db.seed import seed
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_get_profile_known_hcp_includes_seeded_familiarity():
    resp = client.get("/profile/hcp_amara")
    assert resp.status_code == 200
    body = resp.json()
    assert body["hcp_id"] == "hcp_amara"
    assert body["specialty"]
    assert body["familiarity"]["ibuprofen"] == "expert"


def test_get_profile_unknown_hcp_returns_404():
    resp = client.get("/profile/not_a_real_hcp")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail** -- expect `NotImplementedError`

- [ ] **Step 3: Implement `backend/app/routes/profile.py`**

```python
"""
HCP profile endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Engagement, HCP
from app.personalization.scorer import score_familiarity

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{hcp_id}")
def get_profile(hcp_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Contract:
      -> { "hcp_id": str, "name": str, "specialty": str,
           "familiarity": { drug_id: "new" | "returning" | "expert" } }
    """
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if hcp is None:
        raise HTTPException(status_code=404, detail=f"Unknown hcp_id: {hcp_id}")

    drug_ids = [
        row.drug_id
        for row in db.query(Engagement).filter(Engagement.hcp_id == hcp_id).all()
    ]
    familiarity = {drug_id: score_familiarity(hcp_id, drug_id) for drug_id in drug_ids}

    return {
        "hcp_id": hcp.id,
        "name": hcp.name,
        "specialty": hcp.specialty,
        "familiarity": familiarity,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit** -- `git add backend/app/routes/profile.py backend/tests/test_profile.py && git commit -m "Implement GET /profile/{hcp_id}"`

---

### Task 9: `GET /drug/{drug_id}/summary`

**Files:** Modify `backend/app/routes/drug.py` (implement `get_summary`; leave the merged-in `ask_question` as-is); Test `backend/tests/test_drug_summary.py` (new)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_drug_summary.py
import pytest
from fastapi.testclient import TestClient

from app.db.database import init_db
from app.db.seed import seed
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_summary_reflects_seeded_expert_tier():
    resp = client.get("/drug/ibuprofen/summary", params={"hcp_id": "hcp_amara"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "expert"
    assert len(body["bullets"]) > 0


def test_summary_new_hcp_gets_new_tier_and_different_content():
    expert_resp = client.get("/drug/ibuprofen/summary", params={"hcp_id": "hcp_amara"})
    new_resp = client.get("/drug/ibuprofen/summary", params={"hcp_id": "hcp_priya"})
    assert new_resp.json()["tier"] == "new"
    assert new_resp.json()["bullets"] != expert_resp.json()["bullets"]


def test_summary_unknown_drug_returns_404():
    resp = client.get("/drug/not_a_real_drug/summary", params={"hcp_id": "hcp_amara"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail** -- expect `NotImplementedError`

- [ ] **Step 3: Implement `get_summary` in `backend/app/routes/drug.py`** (keep the merged-in `ask_question` and its imports untouched; add these imports and replace only `get_summary`)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Drug
from app.personalization.scorer import build_summary_content, score_familiarity

router = APIRouter(prefix="/drug", tags=["drug"])


@router.get("/{drug_id}/summary")
def get_summary(drug_id: str, hcp_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Contract (see Models/DrugSummary.swift):
      -> { "drug_id": str, "name": str, "tier": "new" | "returning" | "expert",
           "headline": str, "bullets": list[str] }
    """
    drug = db.query(Drug).filter(Drug.id == drug_id).first()
    if drug is None:
        raise HTTPException(status_code=404, detail=f"Unknown drug_id: {drug_id}")

    tier = score_familiarity(hcp_id, drug_id)
    headline, bullets = build_summary_content(drug_id, tier)

    return {
        "drug_id": drug.id,
        "name": drug.name,
        "tier": tier,
        "headline": headline,
        "bullets": bullets,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit** -- `git add backend/app/routes/drug.py backend/tests/test_drug_summary.py && git commit -m "Implement GET /drug/{drug_id}/summary with tier-based content"`

---

### Task 10: End-to-end integration test

**Files:** Test `backend/tests/test_end_to_end.py` (new). Mocks `generate_answer` so this test has no network/API-key dependency.

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_end_to_end.py
import pytest
from fastapi.testclient import TestClient

from app.db.database import init_db
from app.db.seed import seed
from app.main import app
import app.routes.drug as drug_route

client = TestClient(app)


@pytest.fixture(autouse=True)
def _seeded_db():
    init_db()
    seed()


def test_full_scan_ask_rescan_flow(monkeypatch):
    detect_resp = client.post("/detect", json={"barcode": "3-00000-00171", "ocr_text": None})
    assert detect_resp.status_code == 200
    drug_id = detect_resp.json()["drug_id"]
    assert drug_id == "ibuprofen"

    hcp_id = "hcp_priya"

    summary1 = client.get(f"/drug/{drug_id}/summary", params={"hcp_id": hcp_id}).json()
    assert summary1["tier"] == "new"

    monkeypatch.setattr(
        drug_route, "generate_answer", lambda query, context: f"Mock answer using {len(context)} sources."
    )
    ask_resp = client.post(f"/drug/{drug_id}/ask", json={"hcp_id": hcp_id, "query": "What is this used for?"})
    assert ask_resp.status_code == 200
    assert "answer_text" in ask_resp.json()

    for _ in range(3):
        log_resp = client.post("/engagement/log", json={"hcp_id": hcp_id, "drug_id": drug_id})
        assert log_resp.status_code == 200
    assert log_resp.json()["touch_count"] == 3

    summary2 = client.get(f"/drug/{drug_id}/summary", params={"hcp_id": hcp_id}).json()
    assert summary2["tier"] == "expert"
    assert summary2["bullets"] != summary1["bullets"]

    profile_resp = client.get(f"/profile/{hcp_id}")
    assert profile_resp.json()["familiarity"][drug_id] == "expert"
```

- [ ] **Step 2: Run the full test suite** -- `cd backend && .venv/bin/python3 -m pytest -v` -- all PASS. This is the test that pins CLAUDE.md's core requirement ("the same HCP scanning the same drug twice must visibly get a different, more advanced answer").

- [ ] **Step 3: Commit** -- `git add backend/tests/test_end_to_end.py && git commit -m "Add end-to-end test covering the full personalization loop"`

---

### Task 11: Merge back and push

- [ ] **Step 1: Run the full test suite once more from a clean DB** -- `cd backend && rm -f hcp.db && .venv/bin/python3 -m pytest -v` -- all PASS.

- [ ] **Step 2: Exit the worktree** with `action: "keep"`.

- [ ] **Step 3: From the main checkout, create/fast-forward `llm-rag` to this branch's tip**

```bash
git fetch origin
git checkout -b llm-rag origin/llm-rag   # only if no local llm-rag branch exists yet
git merge <worktree-branch-name>
```

- [ ] **Step 4: Run tests once more in the main checkout's own venv**

- [ ] **Step 5: Push** -- `git push origin llm-rag`

- [ ] **Step 6: Report to the user** what branch the integrated backend lives on, that `uvicorn app.main:app --reload` now serves a fully working demo loop, and that `OPENAI_API_KEY` (or `XAI_API_KEY` if switched back to the commented Grok path) must be set for `/drug/{id}/ask` to return real (non-mocked) answers.
