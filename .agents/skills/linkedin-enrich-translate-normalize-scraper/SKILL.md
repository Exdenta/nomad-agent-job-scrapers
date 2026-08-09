---
name: linkedin-enrich-translate-normalize-scraper
description: Search, parse, validate, or integrate normalized LinkedIn jobs with the Apify Actor nomad-agent/linkedin-enrich-translate-normalize-scraper. Use when a Codex or Claude agent needs to find LinkedIn jobs through Apify MCP, configure a bounded Actor run, interpret nomad-agent-job-v1 output, flatten results for a table, or troubleshoot this Actor's input, authentication, run, or dataset contract.
---

# LinkedIn normalized job search

Use the Apify Actor through MCP when available. Keep its nested normalized
record as the system of record; flatten only for a destination that requires
table-shaped values.

The skill and MCP connection are separate: installing this skill does not
configure Apify, authorize an account, or store an API token. If Apify tools
are unavailable, read [references/client-setup.md](references/client-setup.md)
and give the user the setup steps for their client. Prefer hosted Streamable
HTTP with OAuth. Never ask for a token in chat or write one to a repository.

## Before a run

1. Fetch the deployed Actor details or inspect its MCP tool schema.
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
an input or explaining filters, multi-search, translation, enrichment, or
dedupe.

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
  "aiEnrichment": false,
  "includeRaw": false,
  "dedupe": {
    "enabled": false,
    "key": "",
    "stateResetAcknowledged": false
  },
  "analyticsEnabled": false
}
```

Apply these rules:

- Use `postedWithin`; do not invent `timeFilter` or `postedSince`.
- Use `workArrangements` for any union of `remote`, `hybrid`, and `onsite`.
- Start at `maxItems: 5`; set it between 1 and 200 for normal runs. Use 0 only
  when the user explicitly requests the Actor's full bounded 200-item window.
- Inspect the Actor details for current pricing before a paid run. Explain the
  larger result count and any additional per-result cost before increasing
  `maxItems` or enabling translation or AI enrichment.
- Do not request customer DeepL/OpenRouter keys. These features are
  owner-managed.
- Leave cross-run dedupe disabled for one-off searches. Enabling it requires a
  deliberate alert/profile scope and the reset acknowledgement defined by the
  deployed input schema.
- Keep analytics off unless the user explicitly opts in.

## Execute with MCP

1. Call the exact Actor
   `nomad-agent/linkedin-enrich-translate-normalize-scraper`.
2. If the returned run is `READY`, `RUNNING`, `TIMING-OUT`, or `ABORTING`, use
   its run ID with `get-actor-run` and follow `nextStep` until the run is
   terminal.
3. Continue only when the terminal status is `SUCCEEDED`. Read the default
   dataset ID from `storages.datasets.default.id`, then call
   `get-dataset-items`. Paginate with the tool's offset/limit controls when the
   requested result set exceeds one page; never treat an output preview as the
   complete dataset.
4. Treat `SUCCEEDED` with zero dataset items as a valid empty search. Report
   that no matching rows were returned; do not invent a job or retry merely
   because the dataset is empty.
5. Treat `FAILED`, `TIMED-OUT`, and `ABORTED` as errors. Report the run ID,
   status, status message, and exit code. Do not fetch or present a partial
   dataset as a successful result.
6. Treat MCP as the live authentication and execution layer. Do not read an
   `APIFY_TOKEN` from project files or pass one as Actor input.
7. Do not retry a paid run automatically after an ambiguous timeout. Inspect
   the run first to avoid duplicate charges.

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

When answering a user:

- display title, company, locations, workplace arrangement, posting date, and
  posting/application links;
- keep unknown values unknown; do not turn a missing workplace badge into
  `onsite`;
- preserve `null` versus `[]` in the canonical result;
- call only named people hiring contacts;
- distinguish the job URL (`identity.url`) from an external application URL
  (`data.application.url`);
- say whether values came from static source parsing or optional null-only LLM
  enrichment when provenance matters.

## Integration boundary

The flat mapper emits `nomad-agent-flat-job-v1` with primitive values suitable
for Sheets, Airtable, n8n, and Make. Its `jobKey` is the dedupe identity. Array
columns are compact JSON strings so JSON consumers can distinguish `null`,
`[]`, and populated arrays.

The flat projection omits deep fields. Retain the canonical dataset whenever a
consumer needs requirements, contacts, board-specific extensions, provenance,
or complete raw source data.
