---
name: linkedin-enrich-translate-normalize-scraper
description: Find and integrate public LinkedIn jobs with the Apify Actor job-atlas/linkedin-enrich-translate-normalize-scraper. Use to build bounded searches, preserve and validate nomad-agent-job-v1 records, connect through Apify MCP, flatten results for tables, or troubleshoot the Actor contract.
---

# LinkedIn job search with structured output

Use the Apify Actor through MCP when available. Keep its nested normalized
record as the system of record; flatten only for a destination that requires
table-shaped values.

The skill and MCP connection are separate: installing this skill does not
configure Apify, authorize an account, or store an API token. If Apify tools
are unavailable, read [references/client-setup.md](references/client-setup.md)
and give the user the setup steps for their client. Prefer hosted Streamable
HTTP with OAuth. Never ask for a token in chat or write one to a repository.

## Before a run

1. Fetch the deployed Actor details or inspect its MCP tool schema. Use `latest` and check the current input schema before running. Record the returned numeric build number and immutable build ID.
2. Confirm that the deployed input accepts
   `schemaVersion: nomad-agent-job-search-input-v1`. If it does not, explain
   that the deployed schema differs from this skill and do not guess field
   names.
3. Ask only for material missing search choices: keyword, location, freshness,
   workplace arrangement, and maximum results.
4. For a first or exploratory run, default `maxItems` to 5. Increase it only
   when the user asks for a larger result set.
5. Default optional paid or stateful features to off unless the user requested
   them.

Read [references/input-contract.md](references/input-contract.md) when building
an input or explaining filters, multi-search, strict geography, public company
profiles/filters, translation, enrichment, or dedupe.

## Build the input

Always send the input contract discriminator:

```json
{
  "schemaVersion": "nomad-agent-job-search-input-v1",
  "keyword": "TypeScript developer",
  "location": "Spain",
  "postedWithin": "7d",
  "workArrangements": ["remote", "hybrid"],
  "maxItems": 5,
  "translateToEnglish": false,
  "aiEnrichment": {"enabled": false, "accuracy": "silver"},
  "includeRaw": false,
  "dedupe": {
    "enabled": false,
    "key": ""
  },
  "analyticsEnabled": false
}
```

Apply these rules:

- Use `postedWithin`; do not invent `timeFilter` or `postedSince`.
- Use `workArrangements` for any union of `remote`, `hybrid`, and `onsite`.
- Start at `maxItems: 5`; set it between 1 and 1,000 for normal runs. Use 0
  only when the user explicitly requests the Actor's full bounded 1,000-item
  window.
- Omit `firstRunMode` in ordinary programmatic searches. Use it only when the
  user explicitly wants the five-result paid evaluation preset and accepts
  its enrichment and translation events.
- Inspect the Actor details for current pricing before a paid run. Explain the
  larger result count and any additional per-result cost before increasing
  `maxItems` or enabling translation or AI enrichment.
- AI enrichment accepts `{"enabled": true, "accuracy": "silver"}` or
  `{"enabled": true, "accuracy": "gold"}`. Silver is the default accuracy
  when enrichment is enabled; compare deployed prices before selecting Gold.
- No customer model or translation provider keys are required for these
  managed features.
- Leave cross-run dedupe disabled for one-off searches. Enabling it requires a
  deliberate alert/profile scope defined by the deployed input schema.
- Keep analytics off unless the user explicitly opts in.

## Execute with MCP

1. Call generic `call-actor` with this outer envelope. Select build `latest` in
   `callOptions.build`; keep the item and charge limits in the same call options:

   ```json
   {
     "actor": "job-atlas/linkedin-enrich-translate-normalize-scraper",
     "input": {"schemaVersion": "nomad-agent-job-search-input-v1", "maxItems": 5},
     "waitSecs": 0,
     "callOptions": {"build": "latest", "maxItems": 5, "maxTotalChargeUsd": 0.1}
   }
   ```
2. If the returned run is `READY`, `RUNNING`, `TIMING-OUT`, or `ABORTING`, use
   its run ID with `get-actor-run` and follow `nextStep` until the run is
   terminal.
3. Continue only when the authoritative terminal run has status `SUCCEEDED`,
   exit code `0`, and a numeric build number and immutable build ID that match the start response. If an MCP response omits
   `buildNumber`, verify the same run through Apify's authenticated run API;
   omission is not proof of the requested build.
4. Read that run's default key-value-store ID from
   `storages.keyValueStores.default.id` or `defaultKeyValueStoreId`. Call
   `get-key-value-store-record` for `RUN-SUMMARY`, validate it with
   `scripts/validate_run_summary.py`.
5. Read that successful run's default dataset ID from
   `storages.datasets.default.id` or `defaultDatasetId`, then call
   `get-dataset-items`.
   Paginate with the tool's offset/limit controls when the requested result set
   exceeds one page; never treat an output preview as the complete dataset.
6. Require the complete dataset row count to equal `RUN-SUMMARY.delivered`.
   Treat validated `empty` plus zero dataset items as no matching jobs.
7. If a valid usable `partial` outcome has `retry.recommended: true`, wait the
   bounded v4 `afterSeconds` delay and repeat the same input, `latest` selector, item cap, and charge cap
   at most once. Never retry `empty` or a failed Apify run.
8. After the one-retry bound, use the selected attempt’s valid usable dataset and reconcile
   its row count. Missing or invalid summaries stop delivery.
9. Treat `FAILED`, `TIMED-OUT`, and `ABORTED` as errors. Report the run ID,
   status, status message, and exit code. Do not fetch or present a partial
   dataset as a successful result.
10. Treat MCP as the live authentication and execution layer. Do not read an
   `APIFY_TOKEN` from project files or pass one as Actor input.
11. After an ambiguous timeout, inspect the existing run by ID before proposing
   any new paid execution, to avoid duplicate charges.

If MCP is not configured, use `references/client-setup.md`. Never ask the user
to paste an Apify token into chat or source files.

For ready-to-use prompts, read
[references/search-examples.md](references/search-examples.md). Adapt only the
search choices and cost-sensitive options the user requested.

## Validate and present results

Every canonical item must have exactly:

```text
schemaVersion, identity, data, custom, llm, raw
```

Use `scripts/parse_output.py` for structural validation and a lossless
convenience view:

```bash
python3 scripts/parse_output.py actor-output.json --output parsed.json
```

Use `scripts/flatten_output.py` only for a table-oriented destination:

```bash
python3 scripts/flatten_output.py actor-output.json --output flat.json
```

Read [references/output-contract.md](references/output-contract.md) when
interpreting nested values or debugging a rejected record.
Read [references/run-summary.md](references/run-summary.md) when interpreting
run status or explaining why delivery stopped.

When answering a user:

- display title, company, locations, workplace arrangement, posting date, and
  posting/application links;
- keep unknown values unknown; do not turn a missing workplace badge into
  `onsite`;
- preserve `null` versus `[]` in the canonical result;
- call only named people hiring contacts;
- distinguish the job URL (`identity.url`) from an external application URL
  (`data.application.url`);
- say whether values were source-established or added by optional null-only
  enrichment when provenance matters.

## Integration boundary

The flat mapper emits `nomad-agent-flat-job-v1` with primitive values suitable
for Sheets, Airtable, n8n, and Make. Its `jobKey` is the dedupe identity. Array
columns are compact JSON strings so JSON consumers can distinguish `null`,
`[]`, and populated arrays.

The flat projection omits deep fields. Retain the canonical dataset whenever a
consumer needs requirements, contacts, board-specific extensions, provenance,
or complete raw source data.
