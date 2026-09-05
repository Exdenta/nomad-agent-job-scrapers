---
name: euraxess-enrich-translate-normalize-scraper
description: Find EURAXESS research jobs through Apify, validate the nested job records and run outcome, and export results for apps or tables. Use for EURAXESS searches, integrations and output validation.
---

# EURAXESS Jobs Scraper | Full Details & AI Enrichment

Use exact build `1.0.28`. Verify access and current pricing with `fetch-actor-details` before a paid run. Installing this skill does not configure or authorize Apify; use [client setup](references/client-setup.md) if tools are unavailable. Never request an API token in chat.

## Search

Use generic MCP `call-actor` with this complete envelope. Adapt the keyword and location to the request; leave optional paid features off unless requested.

```json
{
  "actor": "nomad-agent/euraxess-enrich-translate-normalize-scraper",
  "input": {
    "schemaVersion": "nomad-agent-job-search-input-v1",
    "keyword": "research",
    "postedWithin": "30d",
    "maxItems": 5,
    "dedupe": {"enabled": false, "key": ""},
    "aiEnrichment": {"enabled": false, "accuracy": "silver"},
    "translateToEnglish": false,
    "includeRaw": false,
    "analyticsEnabled": false
  },
  "waitSecs": 0,
  "callOptions": {"build": "1.0.28", "maxItems": 5, "maxTotalChargeUsd": 0.1}
}
```

Location matches published text; it is not a geocoder or proof of on-site work. `postedWithin` accepts `24h`, `7d`, `30d`, or `any`, not `1h`. Dates use UTC calendar cutoffs: `24h` includes today and yesterday. A run returns at most 200 jobs; `maxItems: 0` also means 200. Dedupe is off by default; enable it deliberately for repeat alerts.

Read [input details](references/input-contract.md) only for filters, workplace constraints, keyword translation, enrichment or alert scopes. Read [search examples](references/search-examples.md) for additional queries.

## Accept results

1. Poll the returned run ID with `get-actor-run` until terminal, bounded by its configured timeout. Require `SUCCEEDED`, exit code `0` and `buildNumber: "1.0.28"`. If MCP omits the build, check the same run through the authenticated API. Stop before dataset retrieval on a missing or different build, `FAILED`, `TIMED-OUT` or `ABORTED`.
2. Read the same run's default key-value-store `RUN-SUMMARY` with `get-key-value-store-record`. Validate it using `scripts/validate_run_summary.py`. Missing or invalid summaries stop delivery. See [summary semantics](references/run-summary.md) for details.
3. Paginate the same run's default dataset with `get-dataset-items`. Its full count must equal `RUN-SUMMARY.delivered`. A valid `empty` with zero rows is an empty search. `empty-limited` means the limits prevented a conclusive search; report that limitation.
4. Only a usable `partial` with `retry.recommended: true` may be retried. Wait `afterSeconds` (1–3600 seconds), repeat the exact input, build, item cap and charge cap at most once, then validate the selected run and reconcile its rows. Never automatically retry other outcomes.

## Preserve and present facts

Run `python3 scripts/parse_output.py actor-output.json --output parsed.json` to validate and retain the canonical record. Its roots are exactly `schemaVersion`, `identity`, `data`, `custom`, `llm`, `raw`. Use `scripts/flatten_output.py` only when a destination needs a table; keep the nested record as the source of truth.

Present title, institution, location, deadline and source link. `null` means unknown; `[]` means an explicitly empty list. Academic-level taxonomy is not an education requirement. Only named people count as hiring contacts. Show optional enrichment status and preserve source facts. Sanitize raw HTML before rendering it.

Read [output details](references/output-contract.md) for field mappings, schema migration and a sample. Local validation or an Actor run does not prove that a hosted workflow wrote to a destination.
