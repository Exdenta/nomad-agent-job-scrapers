# MCP quickstart

The maintained LinkedIn MCP v1 pack is
[`integrations/mcp/README.md`](../integrations/mcp/README.md). It contains:

- credential-free OAuth setup for Codex, Claude Code, Cursor, and eligible
  ChatGPT workspaces;
- environment-backed token alternatives;
- deployed Actor schema and pricing inspection with `fetch-actor-details`;
- exact-build `call-actor` and run/status/dataset helper workflow;
- terminal Actor status, minimal v3 `RUN-SUMMARY`, authoritative build,
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
`callOptions.build: "1.0.9"`, `callOptions.maxItems`, and a conservative
`callOptions.maxTotalChargeUsd`; require the run to report build `1.0.9`.
Validate terminal success and the exact build, read and validate minimal v3
`RUN-SUMMARY`, honor at most one retry, then validate and reconcile the default dataset. Do not
reuse LinkedIn source-specific input fields or destination live-validation
claims for EURAXESS.

Hosted MCP end-to-end smokes passed for exact LinkedIn build `0.6.39` and
EURAXESS build `1.0.9` on 2026-08-13. They validated the original run's factual
v3 status and reconciled dataset, without starting a retry. LinkedIn run
`2pImGZgoQ0a5jGIMW` returned five rows; EURAXESS run `iEv1eNiPgDmysJhAh`
returned a valid empty result. Destination-platform credentials and writes
remain separate validation boundaries.
