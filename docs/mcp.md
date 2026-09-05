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

## EURAXESS profile

EURAXESS has a separate repository skill and compatibility endpoint:

```text
https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

Read the skill's
[client setup](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/client-setup.md)
before use. Use generic `call-actor` with
`callOptions.build: "latest"`, `callOptions.maxItems`, and a conservative
`callOptions.maxTotalChargeUsd`; record the completed run’s immutable `buildId` and numeric `buildNumber`.
Validate terminal success and the returned build evidence, read and validate minimal v4
`RUN-SUMMARY`, honor at most one retry, then validate and reconcile the default dataset. Do not
reuse LinkedIn source-specific input fields for EURAXESS.

The maintained profiles and smoke harness target LinkedIn `1.0.2` and
EURAXESS `latest`. A successful Actor or MCP check confirms only the Actor,
completion record, and dataset path. Destination-platform writes require a
separate test with the client's own credentials and disposable destination.
