# MCP: normalized LinkedIn and EURAXESS jobs

Use the generic Apify MCP tools so every paid run has an exact build and cost
cap:

```text
https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

| Profile | Actor | Exact build |
| --- | --- | --- |
| LinkedIn | `nomad-agent/linkedin-enrich-translate-normalize-scraper` | `0.6.38` |
| EURAXESS | `nomad-agent/euraxess-enrich-translate-normalize-scraper` | `1.0.8` |

Keep the build explicit even when a movable tag currently points to the same
version. EURAXESS is private and requires account access.

## Client configuration

OAuth and environment-token examples are provided for Claude Code, Cursor, and
Codex under [`configs/`](configs). OAuth is preferred. Token examples read
`APIFY_TOKEN` from the process environment and never embed its value.

Eligible ChatGPT web workspaces can add the same hosted Streamable HTTP server
as a custom connector. Custom MCP connectors are available to Business, Enterprise, and Edu workspaces subject to workspace policy.

Before a paid run, use `fetch-actor-details` to check access, the deployed input schema,
current pricing, and availability. Start from the bounded envelopes in
[`examples/`](examples): at most five items, a `$0.10` charge cap, translation
and AI enrichment disabled, raw output disabled, analytics disabled, and
cross-run dedupe disabled.

## Factual status and dataset execution contract

1. Call `call-actor` with `actor`, strict v1 `input`, `waitSecs: 0`, and
   `callOptions` containing the exact build, `maxItems`, and
   `maxTotalChargeUsd`.
2. Poll non-terminal runs with `get-actor-run` until terminal.
3. Continue only for terminal run status `SUCCEEDED`. Treat `FAILED`,
   `TIMED-OUT`, and `ABORTED` as errors and report the run ID, status message,
   and exit code.
4. Verify the exact build. The MCP run projection can omit `buildNumber`, so the
   smoke script re-reads `GET /v2/actor-runs/{runId}` through the Apify REST API
   using the same bearer token.
5. Resolve `storages.keyValueStores.default.id`, read `RUN-SUMMARY` with
   `get-key-value-store-record`, and validate the closed
   `nomad-agent-fleet-run-summary-v2` contract. Continue only for factual
   status `succeeded` or `empty` and the matching source status.
6. Read the same run's default dataset with `get-dataset-items`, paginate when
   necessary, and require its total row count to equal `RUN-SUMMARY.delivered`.
7. Require every row to be `nomad-agent-job-v1` with exactly `schemaVersion`,
   `identity`, `data`, `custom`, `llm`, and `raw` at the top level, plus the
   expected `identity.source`.
8. Treat a validated `empty` summary with zero dataset rows as “no matching
   jobs.” Do not broaden the search or invent a row.

There is no automatic retry. `RUN-SUMMARY` is factual evidence only:
`errors[].retryable` describes whether the failed operation might succeed if a
caller later chooses a new run; it is not permission to schedule one. Missing,
invalid, `partial`, `failed`, or `deadline` summaries stop delivery. A user or
operator can explicitly approve a new paid run after checking the first run.

## Smoke test

Discovery only:

```bash
APIFY_TOKEN=... python3 integrations/mcp/scripts/smoke_test.py --profile linkedin
APIFY_TOKEN=... python3 integrations/mcp/scripts/smoke_test.py --profile euraxess
```

One bounded live run:

```bash
APIFY_TOKEN=... python3 integrations/mcp/scripts/smoke_test.py --profile linkedin --run
APIFY_TOKEN=... python3 integrations/mcp/scripts/smoke_test.py --profile euraxess --run
```

The script never prints the token. It verifies terminal success and the exact
build through REST, validates the factual fleet-v2 status, fetches at most five
rows, reconciles the delivered count, and validates the six-root dataset
contract. It never starts an automatic retry.

## Current validation boundary

Apify metadata was checked on 2026-08-13: LinkedIn `latest` and `canary` point
to `0.6.38`; EURAXESS `latest` and `canary` point to private build `1.0.8`.
Authenticated no-run MCP discovery passed for both profiles with protocol
`2025-06-18`.

A bounded LinkedIn `0.6.38` Actor run and a bounded EURAXESS `1.0.8` date-window
Actor run passed on 2026-08-13. Both wrote valid factual fleet-v2 status and
reconciled their default datasets. These were Actor/API release smokes, not
MCP-client or destination-platform smokes; the checked-in MCP smoke script still
needs a credentialed run through each client path.

No n8n, Make, Google Sheets, Airtable, or webhook destination is validated by
an MCP discovery or Actor-only smoke.
