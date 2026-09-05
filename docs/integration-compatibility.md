# Integration compatibility matrix

Supported release builds:

| Actor | Exact build | Current input fields |
| --- | --- | --- |
| LinkedIn | `latest` | `firstRunMode`, `schemaVersion`, `keyword`, `location`, `linkedinSearch`, `strictGeography`, `workArrangements`, `postedWithin`, `filters`, `companyProfileEnrichment`, `companyFilters`, `maxItems`, `translateToEnglish`, `aiEnrichment`, `includeRaw`, `dedupe`, `analyticsEnabled` |
| EURAXESS | `latest` | `schemaVersion`, `keyword`, `location`, `euraxessSearch`, `workArrangements`, `postedWithin`, `filters`, `maxItems`, `translateToEnglish`, `aiEnrichment`, `includeRaw`, `dedupe`, `analyticsEnabled` |
| AI Job Search & Fit Scorer | `latest` | `mode`, `search`, `jobs`, `sourceDatasetId`, `sourceActorRunId`, `expectedSourceBuild`, `maxItems`, exactly one of `candidateProfile`/`resume`/`resumeText`, `preferences`, `resultMode`, `minDeliveryScore`, `minRankToForward`, `maxAiItems`, `recoverHolds`, `aiConcurrency` |

The LinkedIn and EURAXESS Actors return the six-root `nomad-agent-job-v1` dataset envelope and the
minimal `nomad-agent-run-summary-v4` completion record. Source-specific inputs
and custom output fields are not interchangeable.

The fit scorer consumes canonical jobs but returns
`nomad-ai-job-fit-v1` plus current `nomad-ai-job-fit-run-summary-v4`.
Maintained consumers also accept legacy v3. It is not a third
scraper profile and must not be sent through the flat-job mapper.

## Integration parity

| Integration | LinkedIn build | EURAXESS build | Input support | Output handling |
| --- | --- | --- | --- | --- |
| n8n | `latest` | `latest` | Safe starter fields plus `advancedInputJson` for every current input | The tracker validates v4 and the dataset; the alert starter validates exact canonical rows from a bounded synchronous run |
| Make | Task selects `latest` | Task selects `latest` | The Apify Task owns the complete Actor input | Validates completion and projects the completed dataset |
| MCP | `callOptions.build: "latest"` | `callOptions.build: "latest"` | The complete Actor input is passed under `input` | Verifies terminal status, v4, exact build, retry bound, and canonical rows |
| REST API and webhooks | `build=latest` | `build=latest` | The request body is the complete Actor input | Polls or re-reads the completed run, validates v4, and paginates the dataset |
| Agent Skills | Exact-build MCP profile | Exact-build MCP profile | Source-specific references cover every current field | Keeps canonical output; flattens only for a destination |
| Python parser and flat mapper | Caller verifies build | Caller verifies build | Post-run processing only | Validates source-specific canonical rows and produces the shared projection |
| Airtable | Upstream runner selects build | Upstream runner selects build | Destination only | Uses the shared 32-field projection and `jobKey` idempotency |

## AI Job Search & Fit Scorer parity

| Integration | Exact build | Input support | Output handling | Live channel boundary |
| --- | --- | --- | --- | --- |
| n8n | `latest` | Bounded shortlist starter; edit the complete strict Actor input in Configuration | Validates v3/v4, result-policy billing, and fit rows; projects 21 columns and upserts by `matchKey` | Artifact and Actor run tested; import and named Sheet write not tested |
| Make | Task uses `latest` | The Apify Task owns the complete Actor input and charge cap | Native filters separate legacy v3, v4 shortlist, and v4 audit; projects and upserts by `matchKey` | Artifact and Actor run tested; import and named Sheet write not tested |
| MCP | `callOptions.build: "latest"` | Complete bounded shortlist input under `input` | Caller verifies exact run, v4 policy summary, fit dataset, and charges | Descriptor validated; hosted MCP call not tested |
| REST API | `build=latest` | Complete Actor input | Boundedly reconciles run/storage/charge receipts and validates v3/v4 plus shortlist/audit semantics | Exact v4 Actor canaries passed; this updated client has offline execution coverage but was not used to create a fresh paid run |
| Zapier | Editor uses `latest` | Editor specification carries the bounded shortlist starter | Filters to scored rows at the delivery threshold, then updates or creates by `matchKey` | Editor build and named Sheet write not tested |
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
| Actor, REST recipe, Agent Skill | `latest` (`6aqB3jicww58310qm`) | Actor execution and public-schema validation; hosted MCP and named destinations remain untested |

Input fields: `firstRunMode`, `schemaVersion`, `keyword`, `location`,
`workArrangements`, `postedWithin`, `orderBy`, `maxItems`, `ycSearch`, `dedupe`,
`filters`, `aiEnrichment`, `translateToEnglish`, `includeRaw`, `analyticsEnabled`.
Output is `nomad-agent-job-v1`, source `ycombinator_was`, public `ycombinator-v2`
custom extension, and `nomad-agent-run-summary-v4`. Existing n8n, Make, Zapier,
Airtable, and source-specific Python projections have no YC compatibility claim.
See [the guide](ycombinator.md) for bounded API/MCP recipes.
