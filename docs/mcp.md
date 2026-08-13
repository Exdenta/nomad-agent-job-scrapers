# MCP quickstart

The maintained LinkedIn MCP v1 pack is
[`integrations/mcp/README.md`](../integrations/mcp/README.md). It contains:

- credential-free OAuth setup for Codex, Claude Code, Cursor, and eligible
  ChatGPT workspaces;
- environment-backed token alternatives;
- deployed Actor schema and pricing inspection with `fetch-actor-details`;
- exact-build `call-actor` and run/status/dataset helper workflow;
- terminal Actor status, minimal v4 `RUN-SUMMARY`, authoritative build,
  one bounded retry, and dataset-count verification;
- bounded input and prompt examples;
- explicit empty-result and failure behavior;
- an offline validator and credential-safe live smoke script;
- the current live-validation boundary for the deployed Actor.

Use only the scoped hosted endpoint:

```text
https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

Start with OAuth and follow the complete
[MCP v1 instructions](../integrations/mcp/README.md).

## EURAXESS boundary

EURAXESS has a separate repository skill and compatibility endpoint:

```text
https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

Read the skill's
[client setup](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/client-setup.md)
before use. Use generic `call-actor` with
`callOptions.build: "1.0.10"`, `callOptions.maxItems`, and a conservative
`callOptions.maxTotalChargeUsd`; require the run to report build `1.0.10`.
Validate terminal success and the exact build, read and validate minimal v4
`RUN-SUMMARY`, honor at most one retry, then validate and reconcile the default dataset. Do not
reuse LinkedIn source-specific input fields or destination live-validation
claims for EURAXESS.

Actor/API canaries passed for exact LinkedIn build `0.6.41` and EURAXESS build
`1.0.10` on 2026-08-13. They validated v4 and reconciled the selected dataset,
without starting a retry. LinkedIn run `3Q4yWRpCnbU8iYSVk` returned one row;
EURAXESS run `Fgo5aehGjDm3Q7GQF` returned a valid empty result. Prior hosted-MCP
end-to-end smokes used LinkedIn `0.6.40` and EURAXESS `1.0.9` with v3.
Destination-platform credentials and writes remain separate validation
boundaries.
