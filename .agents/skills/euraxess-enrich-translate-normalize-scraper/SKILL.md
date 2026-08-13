---
name: euraxess-enrich-translate-normalize-scraper
description: Find and integrate EURAXESS research and academic jobs with the Apify Actor nomad-agent/euraxess-enrich-translate-normalize-scraper. Use to build bounded searches, preserve and validate nomad-agent-job-v1 plus EURAXESS taxonomy, flatten results for tables, or check deployment compatibility.
---

# EURAXESS research and academic job search

Use this skill for the strict `1.0` EURAXESS contract. Private `latest` and
`canary` both resolve to build `1.0.10`. Installing this skill does not prove
that the private Actor is accessible to the current user.

Use Apify MCP through generic `call-actor` with
`callOptions.build: "1.0.10"`; do not rely on a mutable tag. Keep the nested
normalized record as the system of record; flatten only for a
destination that requires table-shaped values.

The skill and MCP connection are separate. Installing this skill does not
configure Apify, authorize an account, expose a private Actor, or store an API
token. If Apify tools are unavailable, read
[references/client-setup.md](references/client-setup.md). Prefer hosted
Streamable HTTP with OAuth. Never ask for a token in chat or write one to a
repository.

## Compatibility gate before every run

1. Fetch the deployed Actor details to confirm account access and current
   pricing.
2. Use only generic `call-actor` with exact
   `callOptions.build: "1.0.10"`. Require the run response to report
   `buildNumber: "1.0.10"` before accepting its output.
3. Send `schemaVersion: nomad-agent-job-search-input-v1` and the closed
   `euraxessSearch` extension described in
   [references/input-contract.md](references/input-contract.md).
4. Stop before dataset retrieval when the run build differs.
5. Inspect current pricing and availability. Local source metadata is not
   evidence of deployed pay-per-event prices or public access.
6. Ask only for material missing choices: research keyword, card location,
   freshness, explicit workplace arrangement, and maximum results.
7. Start exploratory runs at `maxItems: 5`, set both Actor input `maxItems: 5`
   and `callOptions.maxItems: 5`, and use a conservative
   `callOptions.maxTotalChargeUsd`. Leave optional paid or stateful features
   off unless requested.

## Build a bounded input

Always send the discriminator:

```json
{
  "schemaVersion": "nomad-agent-job-search-input-v1",
  "keyword": "postdoctoral machine learning",
  "location": "Germany",
  "postedWithin": "24h",
  "maxItems": 5,
  "dedupe": {"enabled": false, "key": ""},
  "aiEnrichment": {"enabled": false, "accuracy": "silver"},
  "translateToEnglish": false,
  "includeRaw": false,
  "analyticsEnabled": false
}
```

Apply these rules:

- `location` matches only location/country text established by a EURAXESS
  search card. It is not a geocoder or evidence of on-site work.
- Use `postedWithin`; do not invent `postedSince` or `timeFilter`. EURAXESS
  publication evidence has calendar-date (`YYYY-MM-DD`) granularity, so this
  Actor accepts `24h`, `7d`, `30d`, or `any` and rejects `1h`.
  `24h` uses an inclusive cutoff of the previous UTC calendar date: it includes
  both the current and previous UTC date and may therefore include a posting
  older than 24 elapsed hours. `7d` and `30d` likewise subtract 7 or 30 UTC
  calendar days and include the cutoff date.
- Use `workArrangements` only when the user wants explicit `remote`, `hybrid`,
  or `onsite` evidence. Unknown arrangements fail that filter.
- Use `maxItems` from 1 through 200. `0` means the complete bounded 200-item
  delivery window, never unlimited.
- The optional EURAXESS extension is exactly
  `{"schemaVersion":"nomad-agent-euraxess-search-v1","translateKeywords":true}`.
  It retains the original keyword and requests faithful multilingual
  equivalents; it does not broaden the role or discipline.
- Translation and Silver/Gold enrichment are owner-managed and may add
  pay-per-event charges. Inspect deployed pricing and ask before enabling
  either. Never request customer DeepL or OpenRouter keys.
- Enrichment reads the complete plain-text description and fills only
  allowlisted fields that remain `null`. Static source facts and explicit
  empty arrays win.
- Cross-run dedupe is default-on in the Actor contract. Disable it explicitly
  for one-off searches. Enabling it requires deliberate tenant/profile scope.
- Analytics is an explicit opt-in and remains off by default.

Read [references/input-contract.md](references/input-contract.md) before using
filters, keyword expansion, enrichment, translation, or dedupe.

## Execute through MCP

Only after the compatibility gate passes. Call the MCP tool `call-actor` with
this outer envelope; the documented bounded input above belongs under `input`:

```json
{
  "actor": "nomad-agent/euraxess-enrich-translate-normalize-scraper",
  "input": {"schemaVersion": "nomad-agent-job-search-input-v1", "maxItems": 5},
  "waitSecs": 0,
  "callOptions": {"build": "1.0.10", "maxItems": 5, "maxTotalChargeUsd": 0.1}
}
```

1. Call generic `call-actor`; do not rely on the direct Actor tool or a mutable
   tag.
2. Require the authoritative run to report `buildNumber: "1.0.10"`. If MCP
   omits that field, verify the same run through Apify's authenticated run API.
   A missing or different build is a compatibility failure.
3. Poll `READY`, `RUNNING`, `TIMING-OUT`, or `ABORTING` runs by run ID with
   `get-actor-run` until terminal.
4. Continue to dataset retrieval only after `SUCCEEDED` with exit code `0`.
   Treat `FAILED`, `TIMED-OUT`, and `ABORTED` as errors, report the run ID,
   status, status message, and exit code, and never present a partial dataset
   as success.
5. Read the same run's default key-value-store `RUN-SUMMARY` with
   `get-key-value-store-record`. Validate it with
   `scripts/validate_run_summary.py`.
6. Fetch the default dataset ID from the same successful run and paginate with
   `get-dataset-items`. An output preview is not the complete dataset.
7. Require the complete dataset row count to equal `RUN-SUMMARY.delivered`.
   Accept validated `empty` plus zero rows as a valid empty search.
8. If a valid usable `partial` outcome has `retry.recommended: true`, wait the
   bounded v4 `afterSeconds` delay and repeat the exact input, build, item cap, and charge cap
   at most once. Never retry an empty, failed, timed-out, or aborted run.
9. After the one-retry bound, use the latest valid usable dataset and reconcile
   its row count. Missing or invalid summaries stop delivery.
10. Treat MCP as the live authentication layer. Never read an `APIFY_TOKEN`
    from project files or pass one in Actor input.

See [references/search-examples.md](references/search-examples.md) for bounded
prompts. They are contract examples, not live-validation claims.

## Validate and present output

Every canonical item must have exactly:

```text
schemaVersion, identity, data, custom, llm, raw
```

Validate and create a lossless convenience view:

```bash
python3 scripts/parse_output.py actor-output.json --output parsed.json
```

Create a table projection only when required:

```bash
python3 scripts/flatten_output.py actor-output.json --output flat.json
```

When presenting results:

- show title, organisation, locations, explicit workplace arrangement,
  posting date/deadline, research domains, and posting/application links;
- preserve `null` as unknown and `[]` as source-established empty;
- never derive `onsite` from a city, country, facility, or address;
- keep `custom.data.academicLevelRaw` as EURAXESS board taxonomy rather than
  converting it to applicant education requirements;
- place only named people in `data.application.hiringContacts`;
- treat an anonymous or generic email as an application channel only when it
  is explicitly published under EURAXESS `Where to apply`; emails in the
  `Contact` block stay in raw evidence and are not promoted;
- distinguish the canonical posting URL from a separately established
  application URL or email;
- never promote a search-card snippet to the complete raw description;
- explain optional LLM-filled paths separately from deterministic source
  facts when provenance matters.

Read [references/output-contract.md](references/output-contract.md) for the
normalized and EURAXESS-specific fields.
Read [references/run-summary.md](references/run-summary.md) for the factual
status contract and its one-bounded-retry boundary.

## Integration boundary

The bundled flat mapper emits `nomad-agent-flat-job-v1` primitives suitable
for Sheets, Airtable, n8n, and Make. Arrays are compact JSON strings so JSON
consumers can preserve `null`, `[]`, and populated arrays. The flat projection
omits deep requirements, named contacts, EURAXESS custom fields, availability
evidence, and detailed provenance. Retain the canonical dataset whenever
those facts matter.
