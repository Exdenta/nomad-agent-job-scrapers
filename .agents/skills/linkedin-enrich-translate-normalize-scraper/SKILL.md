---
name: linkedin-enrich-translate-normalize-scraper
description: Search, parse, validate, or integrate normalized LinkedIn jobs with the Apify Actor nomad-agent/linkedin-enrich-translate-normalize-scraper. Use when a user asks an MCP agent to find LinkedIn jobs, configure the Actor, interpret nomad-agent-job-v1 output, flatten results for a table, or troubleshoot this Actor's input and dataset contract.
---

# LinkedIn normalized job search

Use the Apify Actor through MCP when available. Keep its nested normalized
record as the system of record; flatten only for a destination that requires
table-shaped values.

## Before a run

1. Fetch the deployed Actor details or inspect its MCP tool schema.
2. Confirm that the deployed input accepts
   `schemaVersion: nomad-agent-job-search-input-v1`. If it does not, explain
   that the public build predates this skill and do not guess old field names.
3. Ask only for material missing search choices: keyword, location, freshness,
   workplace arrangement, and maximum results.
4. Default optional paid or stateful features to off unless the user requested
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
  "maxItems": 20,
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
- Set `maxItems` between 1 and 200 for normal runs. Use 0 only when the user
  explicitly requests the Actor's full bounded 200-item window.
- Explain additional per-result cost before enabling translation or AI
  enrichment.
- Do not request customer DeepL/OpenRouter keys. These features are
  owner-managed.
- Leave cross-run dedupe disabled for one-off searches. Enabling it requires a
  deliberate alert/profile scope and the reset acknowledgement defined by the
  deployed input schema.
- Keep analytics off unless the user explicitly opts in.

## Execute with MCP

1. Call the exact Actor
   `nomad-agent/linkedin-enrich-translate-normalize-scraper`.
2. Wait for the run to reach a terminal state.
3. If the call returns an output preview, obtain the dataset ID and call
   Apify's `get-actor-output` tool for the complete requested result set.
4. Do not retry a paid run automatically after an ambiguous timeout. Inspect
   the run first to avoid duplicate charges.

If MCP is not configured, direct the user to the repository's `docs/mcp.md`.
Never ask the user to paste an Apify token into chat or source files.

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
