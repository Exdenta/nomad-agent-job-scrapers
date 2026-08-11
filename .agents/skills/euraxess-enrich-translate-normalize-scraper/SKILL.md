---
name: euraxess-enrich-translate-normalize-scraper
description: Search, parse, validate, or integrate normalized EURAXESS research jobs with the Apify Actor nomad-agent/euraxess-enrich-translate-normalize-scraper. Use when an agent needs to prepare a bounded EURAXESS search, inspect the strict v1 input, interpret nomad-agent-job-v1 and EURAXESS custom taxonomy, read fleet-v2 RUN-SUMMARY facts, flatten results for a table, or diagnose deployment-contract mismatches.
---

# EURAXESS normalized research-job search

Use this skill for the clean `1.0` EURAXESS contract. The source currently
deployed under this Actor name is a private older `0.5.1` build; the local
`1.0` rewrite described here is not deployed or Store-published. Never treat
installing this skill as proof that a compatible Actor is available.

Use Apify MCP when it exposes the exact Actor and current schema. Keep the
nested normalized record as the system of record; flatten only for a
destination that requires table-shaped values.

The skill and MCP connection are separate. Installing this skill does not
configure Apify, authorize an account, expose a private Actor, or store an API
token. If Apify tools are unavailable, read
[references/client-setup.md](references/client-setup.md). Prefer hosted
Streamable HTTP with OAuth. Never ask for a token in chat or write one to a
repository.

## Compatibility gate before every run

1. Fetch the deployed Actor details or inspect its MCP tool schema.
2. Require `schemaVersion: nomad-agent-job-search-input-v1` and the closed
   `euraxessSearch` extension described in
   [references/input-contract.md](references/input-contract.md).
3. Stop before execution when the deployed schema differs. In particular, do
   not send this skill's input to the known older `0.5.1` deployment.
4. Inspect current pricing and availability. Local source metadata is not
   evidence of deployed pay-per-event prices or public access.
5. Ask only for material missing choices: research keyword, card location,
   freshness, explicit workplace arrangement, and maximum results.
6. Start exploratory runs at `maxItems: 5`. Leave optional paid or stateful
   features off unless requested.

## Build a bounded input

Always send the discriminator:

```json
{
  "schemaVersion": "nomad-agent-job-search-input-v1",
  "keyword": "postdoctoral machine learning",
  "location": "Germany",
  "postedWithin": "30d",
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

Only after the compatibility gate passes:

1. Call `nomad-agent/euraxess-enrich-translate-normalize-scraper`.
2. Poll `READY`, `RUNNING`, `TIMING-OUT`, or `ABORTING` runs by run ID with
   `get-actor-run` until terminal.
3. Once terminal, read `RUN-SUMMARY` from the run's default key-value store
   when that storage ID is available. Require
   `nomad-agent-fleet-run-summary-v2` and interpret it using
   [references/run-summary.md](references/run-summary.md). The v2 summary
   reports facts; it does not schedule or recommend a retry.
4. Continue to dataset retrieval only after `SUCCEEDED`. Treat `FAILED`,
   `TIMED-OUT`, and `ABORTED` as errors, report the run ID, status, status
   message, exit code, and any valid structured summary, and never present a
   partial dataset as success.
5. Fetch the default dataset ID from the same successful run and paginate with
   `get-dataset-items`. An output preview is not the complete dataset.
6. Accept a successful, explicitly empty run as a valid empty search. Never
   invent a job or retry merely because zero rows were returned.
7. For `partial`, `failed`, or `deadline` summary state, report the bounded
   source facts. Do not parse logs or human messages to invent a retry delay.
8. A missing summary means no structured source-health record was available.
   It is not permission to infer success, blocking, or a retry instruction.
9. Do not automatically retry a paid ambiguous timeout or degraded run.
10. Treat MCP as the live authentication layer. Never read an `APIFY_TOKEN`
    from project files or pass one in Actor input.

Validate a retrieved summary with the validator bundled in every installed
copy of this skill:

```bash
python3 .agents/skills/euraxess-enrich-translate-normalize-scraper/scripts/validate_run_summary.py \
  run-summary.json
```

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

## Integration boundary

The bundled flat mapper emits `nomad-agent-flat-job-v1` primitives suitable
for Sheets, Airtable, n8n, and Make. Arrays are compact JSON strings so JSON
consumers can preserve `null`, `[]`, and populated arrays. The flat projection
omits deep requirements, named contacts, EURAXESS custom fields, availability
evidence, and detailed provenance. Retain the canonical dataset whenever
those facts matter.
