# Scaling path

This is built deliberately small for a 36-hour demo, with specific upgrade points already designed in — not guessed at. Nothing below requires a rewrite; each row upgrades what sits behind an existing interface.

| Component | Tonight | Move when... | Next step |
|---|---|---|---|
| Drug docs | Repo folder | A non-engineer needs to add a dossier without a code deploy | Cloud Storage bucket (GCS or R2) |
| HCP/engagement data | SQLite file | More than one backend instance runs concurrently | Managed Postgres (Cloud SQL, RDS, Supabase) |
| Retrieval index | In-memory, rebuilt at startup | Startup time grows, or need to scale past one machine | Persisted FAISS index, then a managed vector DB (pgvector) |
| LLM | Sponsor's API | Cost/rate limits, or sponsor relationship ends | Own API key + response caching |
| "Auth" | Persona picker | Can't let anyone claim to be any physician anymore | Sign in with Apple, or NPI-verified login |
| Deployment | Single Cloud Run/Render instance | Traffic exceeds one instance | Auto-scaling (no code change needed) |

The pattern: `retrieve()` and the LLM client are each called from exactly one place in the codebase. Whatever is upgraded, callers never change.
