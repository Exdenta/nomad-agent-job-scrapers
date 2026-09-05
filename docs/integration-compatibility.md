# Integration compatibility matrix

Supported release builds:

| Actor | Exact build | Current input fields |
| --- | --- | --- |
| LinkedIn | `1.0.2` | `firstRunMode`, `schemaVersion`, `keyword`, `location`, `linkedinSearch`, `strictGeography`, `workArrangements`, `postedWithin`, `filters`, `companyProfileEnrichment`, `companyFilters`, `maxItems`, `translateToEnglish`, `aiEnrichment`, `includeRaw`, `dedupe`, `analyticsEnabled` |
| EURAXESS | `1.0.16` | `schemaVersion`, `keyword`, `location`, `euraxessSearch`, `workArrangements`, `postedWithin`, `filters`, `maxItems`, `translateToEnglish`, `aiEnrichment`, `includeRaw`, `dedupe`, `analyticsEnabled` |
| AI Job Search & Fit Scorer | `0.1.11` | `mode`, `search`, `jobs`, `sourceDatasetId`, `sourceActorRunId`, `expectedSourceBuild`, `maxItems`, exactly one of `candidateProfile`/`resume`/`resumeText`, `preferences`, `minRankToForward`, `maxAiItems`, `recoverHolds`, `aiConcurrency` |

The LinkedIn and EURAXESS Actors return the six-root `nomad-agent-job-v1` dataset envelope and the
minimal `nomad-agent-run-summary-v4` completion record. Source-specific inputs
and custom output fields are not interchangeable.

The fit scorer consumes canonical jobs but returns
`nomad-ai-job-fit-v1` plus `nomad-ai-job-fit-run-summary-v3`. It is not a third
scraper profile and must not be sent through the flat-job mapper.

## Integration parity

| Integration | LinkedIn build | EURAXESS build | Input support | Output handling |
| --- | --- | --- | --- | --- |
| n8n | `1.0.2` | `1.0.16` | Safe starter fields plus `advancedInputJson` for every current input | The tracker validates v4 and the dataset; the alert starter validates exact canonical rows from a bounded synchronous run |
| Make | Task pins `1.0.2` | Task pins `1.0.16` | The Apify Task owns the complete Actor input | Validates completion and projects the completed dataset |
| MCP | `callOptions.build: "1.0.2"` | `callOptions.build: "1.0.16"` | The complete Actor input is passed under `input` | Verifies terminal status, v4, exact build, retry bound, and canonical rows |
| REST API and webhooks | `build=1.0.2` | `build=1.0.16` | The request body is the complete Actor input | Polls or re-reads the completed run, validates v4, and paginates the dataset |
| Agent Skills | Exact-build MCP profile | Exact-build MCP profile | Source-specific references cover every current field | Keeps canonical output; flattens only for a destination |
| Python parser and flat mapper | Caller verifies build | Caller verifies build | Post-run processing only | Validates source-specific canonical rows and produces the shared projection |
| Airtable | Upstream runner selects build | Upstream runner selects build | Destination only | Uses the shared 32-field projection and `jobKey` idempotency |

## AI Job Search & Fit Scorer parity

| Integration | Exact build | Input support | Output handling | Live channel boundary |
| --- | --- | --- | --- | --- |
| n8n | `0.1.11` | Bounded search starter; edit the complete strict Actor input in Configuration | Validates v3, billing, and fit rows; projects 21 columns and upserts by `matchKey` | Artifact and Actor run tested; import and named Sheet write not tested |
| Make | Task pins `0.1.11` | The Apify Task owns the complete Actor input and charge cap | Native filters validate declared v3 fields; projects and upserts by `matchKey` | Artifact and Actor run tested; import and named Sheet write not tested |
| MCP | `callOptions.build: "0.1.11"` | Complete bounded Actor input under `input` | Caller verifies exact run, v3 summary, fit dataset, and charges | Descriptor validated; hosted MCP call not tested |
| REST API | `build=0.1.11` | Complete Actor input | Boundedly reconciles eventual run/storage receipts and validates the closed fit contract | Exact Actor canary passed; shipped REST client was proven on predecessor `0.1.10` |
| Zapier | Editor pins `0.1.11` | Editor specification carries the bounded complete starter | Filters fit rows, then updates or creates by `matchKey` | Editor build and named Sheet write not tested |
| Python adapter | Caller verifies build | Post-run processing only | Closed-row validation and fit-specific table projection | Offline tested |

## Feature transport rules

- n8n exposes conservative starter fields. `advancedInputJson` can carry every
  field listed above and is merged before the call.
- Make keeps the complete request in an Apify Task so the selected build,
  limits, cost cap, and inputs travel together.
- MCP calls use the generic `call-actor` envelope with an exact build, item
  limit, and cost cap.
- REST clients send the same input JSON accepted by the Actor; fields are not
  renamed or discarded.
- Airtable and Google Sheets are flat destinations. Preserve the canonical
  dataset when nested `custom`, provenance, or raw values are required.

## Validation boundary

The repository test suite checks exact version selectors, all 17 LinkedIn and
13 EURAXESS input fields, template pass-through, terminal-run and v4 status
gates, canonical output, flat projection, secret hygiene, and the hard
one-retry limit.

Actor/API or MCP checks prove the Actor and contract path only. They do not
prove writes to n8n, Make, Google Sheets, Airtable, or a webhook destination.
Destination-specific live validation requires the client's own disposable
destination and credentials. Importing a template supplies no credentials and
does not activate a schedule.

## Y Combinator normalized profile

| Surface | Exact build | Verification boundary |
| --- | --- | --- |
| Actor, REST recipe, Agent Skill | `1.0.6` (`6aqB3jicww58310qm`) | Actor execution and public-schema validation; hosted MCP and named destinations remain untested |

Input fields: `firstRunMode`, `schemaVersion`, `keyword`, `location`,
`workArrangements`, `postedWithin`, `orderBy`, `maxItems`, `ycSearch`, `dedupe`,
`filters`, `aiEnrichment`, `translateToEnglish`, `includeRaw`, `analyticsEnabled`.
Output is `nomad-agent-job-v1`, source `ycombinator_was`, public `ycombinator-v2`
custom extension, and `nomad-agent-run-summary-v4`. Existing n8n, Make, Zapier,
Airtable, and source-specific Python projections have no YC compatibility claim.
See [the guide](ycombinator.md) for bounded API/MCP recipes.
