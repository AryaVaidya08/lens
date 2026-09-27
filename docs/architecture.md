# Scaling path

This started deliberately small for a 36-hour demo, with specific upgrade points designed in from the start — not guessed at. Two rows below have already moved since the original scaffold (HCP/engagement data, and auth); the rest are still where they started. Nothing here requires a rewrite: each row upgrades what sits behind an existing interface.

| Component | Now | Move when... | Next step |
|---|---|---|---|
| Drug docs | Repo folder (`backend/data/drug_docs/`, ~1,800 openFDA-derived dossiers) | A non-engineer needs to add a dossier without a code deploy | Cloud Storage bucket (GCS or R2) |
| HCP/engagement data, accounts | **Already moved:** MongoDB (Atlas or local; `mongomock` in-memory for tests) — this replaced the original SQLite plan | Multi-region latency, or backup/compliance needs beyond what Atlas gives you out of the box | Dedicated Atlas cluster tier, read replicas |
| Retrieval index | In-memory, rebuilt at startup, embedded with `sentence-transformers` | Startup time grows, or need to scale past one machine | Persisted FAISS index, then a managed vector DB (pgvector) |
| LLM | xAI's Grok API (`app/llm/client.py`), with a grounded extractive fallback when no key is configured | Cost/rate limits, or need a different model quality/latency tradeoff | Swap the provider inside `generate_answer()`; response caching |
| Auth | **Already moved:** real accounts — email/password, hashed passwords, bearer session tokens, recovery-code-based reset (`app/routes/auth.py`) — this replaced the original persona-picker plan | Need to verify someone is actually a licensed physician, not just an email owner | NPI-verified login, or Sign in with Apple layered on top of existing sessions |
| Deployment | Single local process (backend + iOS + web dashboard, all on one laptop) | Traffic exceeds one instance, or the demo needs to run without the laptop present | Single Cloud Run/Render instance, then auto-scaling (no code change needed) |

The pattern holds even after the auth/DB moves: `retrieve()` and `generate_answer()` are each called from exactly one place in the codebase (see `CLAUDE.md`'s "two swap points"). Whatever is upgraded next, callers never change.
