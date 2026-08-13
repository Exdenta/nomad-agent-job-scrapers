# MCP: normalized LinkedIn and EURAXESS jobs

Use the generic Apify MCP tools so every paid run has an exact build and cost
cap:

```text
https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

| Profile | Actor | Exact build |
| --- | --- | --- |
| LinkedIn | `nomad-agent/linkedin-enrich-translate-normalize-scraper` | `0.6.45` |
| EURAXESS | `nomad-agent/euraxess-enrich-translate-normalize-scraper` | `1.0.13` |

Keep the build explicit instead of relying on a movable tag. Confirm Actor
availability and account access with `fetch-actor-details` before a paid run.

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

## Public outcome and dataset execution contract

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
   `nomad-agent-run-summary-v4` contract.
6. If a usable `partial` outcome has `retry.recommended: true`, wait the
   bounded delay and repeat the exact paid request at most once.
7. Read the selected run's default dataset with `get-dataset-items`, paginate when
   necessary, and require its total row count to equal `RUN-SUMMARY.delivered`.
8. Require every row to be `nomad-agent-job-v1` with exactly `schemaVersion`,
   `identity`, `data`, `custom`, `llm`, and `raw` at the top level, plus the
   expected `identity.source`.
9. Treat a validated `empty` summary with zero dataset rows as “no matching
   jobs.” Do not broaden the search or invent a row.

Only the closed v4 retry object can request an automatic retry, and the hard
limit is one. Missing or invalid summaries stop delivery. Failed, timed-out,
or aborted Apify runs are never retried from `RUN-SUMMARY`. The record exposes
no source diagnostics.

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
build through REST, validates v4, honors at most one bounded retry, fetches at most five
rows, reconciles the delivered count, and validates the six-root dataset
contract.

## Validation boundary

The maintained profiles and smoke harness target LinkedIn `0.6.45` and
EURAXESS `1.0.13`. The harness contains no credential and verifies the exact
build, terminal result, v4 completion record, delivered count, and canonical
dataset rows.

An MCP or Actor-only smoke does not validate n8n, Make, Google Sheets,
Airtable, or webhook delivery. Test those destinations separately with the
client's own credentials and disposable data.
