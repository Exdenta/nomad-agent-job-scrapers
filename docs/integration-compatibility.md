# Integration compatibility matrix

Supported release builds:

| Actor | Exact build | Current input fields |
| --- | --- | --- |
| LinkedIn | `0.6.42` | `schemaVersion`, `keyword`, `location`, `linkedinSearch`, `strictGeography`, `workArrangements`, `postedWithin`, `filters`, `companyProfileEnrichment`, `companyFilters`, `maxItems`, `translateToEnglish`, `aiEnrichment`, `includeRaw`, `dedupe`, `analyticsEnabled` |
| EURAXESS | `1.0.13` | `schemaVersion`, `keyword`, `location`, `euraxessSearch`, `workArrangements`, `postedWithin`, `filters`, `maxItems`, `translateToEnglish`, `aiEnrichment`, `includeRaw`, `dedupe`, `analyticsEnabled` |

Both Actors return the six-root `nomad-agent-job-v1` dataset envelope and the
minimal `nomad-agent-run-summary-v4` completion record. Source-specific inputs
and custom output fields are not interchangeable.

## Integration parity

| Integration | LinkedIn build | EURAXESS build | Input support | Output handling |
| --- | --- | --- | --- | --- |
| n8n | `0.6.42` | `1.0.13` | Safe starter fields plus `advancedInputJson` for every current input | Validates v4, permits at most one recommended retry, reconciles the dataset, and projects rows |
| Make | Task pins `0.6.42` | Task pins `1.0.13` | The Apify Task owns the complete Actor input | Validates completion and projects the completed dataset |
| MCP | `callOptions.build: "0.6.42"` | `callOptions.build: "1.0.13"` | The complete Actor input is passed under `input` | Verifies terminal status, v4, exact build, retry bound, and canonical rows |
| REST API and webhooks | `build=0.6.42` | `build=1.0.13` | The request body is the complete Actor input | Polls or re-reads the completed run, validates v4, and paginates the dataset |
| Agent Skills | Exact-build MCP profile | Exact-build MCP profile | Source-specific references cover every current field | Keeps canonical output; flattens only for a destination |
| Python parser and flat mapper | Caller verifies build | Caller verifies build | Post-run processing only | Validates source-specific canonical rows and produces the shared projection |
| Airtable | Upstream runner selects build | Upstream runner selects build | Destination only | Uses the shared 32-field projection and `jobKey` idempotency |

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

The repository test suite checks exact version selectors, all 16 LinkedIn and
13 EURAXESS input fields, template pass-through, terminal-run and v4 status
gates, canonical output, flat projection, secret hygiene, and the hard
one-retry limit.

Actor/API or MCP checks prove the Actor and contract path only. They do not
prove writes to n8n, Make, Google Sheets, Airtable, or a webhook destination.
Destination-specific live validation requires the client's own disposable
destination and credentials. Importing a template supplies no credentials and
does not activate a schedule.
