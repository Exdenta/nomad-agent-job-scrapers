# Integration compatibility matrix

Snapshot verified against Apify metadata on 2026-08-13.

| Actor | Supported build | Default-tag boundary | Current input fields |
| --- | --- | --- | --- |
| LinkedIn | `0.6.39` (`BeiVWPUtqRLO7Z68W`) | Public `latest` and `canary` point to `0.6.39` | `schemaVersion`, `keyword`, `location`, `linkedinSearch`, `strictGeography`, `workArrangements`, `postedWithin`, `filters`, `companyProfileEnrichment`, `companyFilters`, `maxItems`, `translateToEnglish`, `aiEnrichment`, `includeRaw`, `dedupe`, `analyticsEnabled` |
| EURAXESS | `1.0.9` (`Mp2Nw9lxoKcuAXQk1`) | Private `latest` and `canary` point to `1.0.9` | `schemaVersion`, `keyword`, `location`, `euraxessSearch`, `workArrangements`, `postedWithin`, `filters`, `maxItems`, `translateToEnglish`, `aiEnrichment`, `includeRaw`, `dedupe`, `analyticsEnabled` |

The two Actors share the six-root `nomad-agent-job-v1` dataset-row envelope and
the same minimal `nomad-agent-run-summary-v3` delivery and one-retry gate. Their source
extensions remain different.

## Integration parity

| Integration | LinkedIn build selection | EURAXESS build selection | Full current input support | Output boundary |
| --- | --- | --- | --- | --- |
| n8n | Workflow pins `0.6.39` | Workflow pins `1.0.9` | Yes. Simple safe fields plus `advancedInputJson`, merged and validated before the paid call | Validates v3, retries once when valid, then reconciles and projects the dataset |
| Make | Apify Task must pin `0.6.39` | Apify Task must pin `1.0.9` | Yes. The Task owns the complete Actor input; the blueprint consumes its completed run | Reads v3 and can repeat the same Task once before projecting rows |
| MCP | Generic `call-actor` pins `callOptions.build: "0.6.39"` | Generic `call-actor` pins `callOptions.build: "1.0.9"` | Yes. Actor input is passed without a reduced integration schema | REST-verified terminal run; validated v3; one retry; reconciled canonical rows |
| REST API and webhooks | `build=0.6.39` | `build=1.0.9` | Yes. JSON request body is the Actor input | Poll/read the exact run, factual status, and dataset; a webhook is only a completion signal |
| Agent skills | LinkedIn pinned generic MCP profile | EURAXESS pinned generic MCP profile | Yes. Each skill documents its source-specific contract | Canonical-first; flatten only for a destination |
| Python parser and flat mapper | Caller verifies the originating run | Caller verifies the originating run | Not applicable: post-run processing | Source-specific canonical validation plus the same flat projection for both Actors |
| Airtable | Upstream runner chooses build | Upstream runner chooses build | Not applicable: destination-only | Shared 32-field projection; retain the canonical record elsewhere when deeper fields are needed |

## Feature transport rules

- n8n's explicit fields form a safe starter input. `advancedInputJson` may
  override them and carries every field listed above. The validation node
  rejects malformed JSON, an unsupported shared schema, invalid freshness or
  workplace values, an unbounded `maxItems`, or a non-version build selector.
- Make blueprints deliberately do not copy Actor input. Configure every input
  feature, exact build, item cap, and charge cap in the Apify Task. That keeps
  every completion bound to the same saved request.
- Both MCP profiles use the generic `call-actor` envelope with an exact build
  and cost caps. The smoke script re-reads authoritative run metadata through
  REST because the MCP run projection can omit `buildNumber`.
- API clients send the same input JSON as Apify Console. The integration does
  not rename or drop Actor fields.
- Airtable and Google Sheets are flat destinations. The projection cannot
  represent every nested `custom`, provenance, or raw value; it therefore does
  not replace the canonical dataset.

## Validation boundary

Repository tests cover configuration parsing, exact version selectors, all
current input-key pass-through, terminal-run and v3 status gating, canonical
output, flat projection, secret hygiene, and the hard one-retry bound. Apify metadata confirms the
build/tag and input-schema facts above. Authenticated hosted-MCP discovery and
end-to-end execution passed on 2026-08-13 for both exact builds with protocol
`2025-06-18`: LinkedIn run `2pImGZgoQ0a5jGIMW` returned five reconciled
canonical rows and EURAXESS run `iEv1eNiPgDmysJhAh` a reconciled valid empty
result. LinkedIn's MCP-origin compatibility layer also
passed 36 tests in the exact hash-locked Python 3.12 / Apify `2.7.3` runtime.

Historical LinkedIn n8n and Make destination tests used older builds. The
current `0.6.39` n8n/Make destination paths and all EURAXESS destinations still
need credentialed live smoke tests. The MCP smoke harness requires an
`APIFY_TOKEN`, but the checked-in scripts contain no credential. Actor/API and
hosted-MCP release smokes passed for LinkedIn `0.6.39` and EURAXESS `1.0.9` on
2026-08-13, and both `latest` tags were moved to those builds. No Task
reconfiguration, n8n or Make destination activation, Airtable write, or Store
publication was part of that Actor rollout.
