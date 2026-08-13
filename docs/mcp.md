# MCP quickstart

The maintained LinkedIn MCP v1 pack is
[`integrations/mcp/README.md`](../integrations/mcp/README.md). It contains:

- credential-free OAuth setup for Codex, Claude Code, Cursor, and eligible
  ChatGPT workspaces;
- environment-backed token alternatives;
- deployed Actor schema and pricing inspection with `fetch-actor-details`;
- exact-build `call-actor` and run/status/dataset helper workflow;
- terminal Actor status, factual fleet-v2 `RUN-SUMMARY`, authoritative build,
  and dataset-count verification with no automatic retry;
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
`callOptions.build: "1.0.8"`, `callOptions.maxItems`, and a conservative
`callOptions.maxTotalChargeUsd`; require the run to report build `1.0.8`.
Validate terminal success and the exact build, read and validate factual
fleet-v2 `RUN-SUMMARY`, then validate and reconcile the default dataset. Do not
reuse LinkedIn source-specific input fields or destination live-validation
claims for EURAXESS.
