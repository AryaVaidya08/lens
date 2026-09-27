# Grok scan summaries

General scans now select reference sections by specialty and familiarity, pass
those complete sections to Grok, and return its compact bullets in `bullets`.
`full_bullets` retains the selected original passages. `summary_source` is `grok`
for a successful generated result and `reference` for the fallback.

The iPhone card and React drug details use `bullets`. The iPhone expanded reader
shows the complete bullets first, with a **Full reference text** disclosure for
the original passages; the web drug view offers the same disclosure. Older
backend responses remain decodable.

The generation request uses xAI's documented
[structured output format](https://docs.x.ai/developers/model-capabilities/text/structured-outputs).
It requests one short bullet per passage, preserving their order, important
warnings, negation, units, and qualifications. Responses are checked for JSON
shape, completeness, item count, duplicate bullets, and length (240 characters /
35 words per bullet). These checks do not independently validate clinical accuracy.

Validated successful results are cached in memory, up to 128 entries, keyed by
drug name, full source text, familiarity, specialty, model, and provider URL.
Failed requests are not cached. Changing familiarity or reference text creates
a different entry. Restarting the backend clears the cache.

When a key is missing, the request times out/fails, the response is invalid, or
selected passages exceed 120,000 characters, the endpoint returns bounded
reference excerpts and the UI explicitly says the AI summary is unavailable.
Original passages remain readable. The existing patient-only scan flow does not
call the general-summary generator or include patient chart information in it.

## Activate live generation

Configure `XAI_API_KEY` in the backend environment or its local `.env` file, and
set `XAI_MODEL` to a model available to that account. The existing defaults use
the xAI API base and the project's configured Grok model. Restart the backend
after setting credentials; keep credentials out of source control and chat.

The environment inspected during implementation had **no configured Grok key**.
Live generation and provider/model access therefore remain unverified. An
authenticated general-summary response with `summary_source: "grok"` confirms
that the generator returned a validated model response (possibly from the
process's success cache). `reference` is not a successful Grok response.

## Validation

Tests cover complete input passages, specialty/familiarity prompts, cache
separation, missing credentials, timeout/retry, invalid JSON, incorrect bullet
counts, oversized output, duplicate bullets, HTTP errors, response contracts,
and keeping patient checks separate. Tests disable live provider calls by default.
Swift contract checks confirm that the compact card uses generated bullets
instead of substituting the full source text.

The broader existing suite also revealed a separate allergy-alias failure:
`test_each_chart_flag[pat_j-Max-Cho-ativan-None-lorazepam-Lorazepam-flag]` currently
returns `clear`. It also fails in isolation and exercises the unchanged chart
matcher, not the new summary generator. It remains unresolved by this change.
