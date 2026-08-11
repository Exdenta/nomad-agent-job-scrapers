# MCP quickstart

The maintained LinkedIn MCP v1 pack is
[`integrations/mcp/README.md`](../integrations/mcp/README.md). It contains:

- credential-free OAuth setup for Codex, Claude Code, Cursor, and eligible
  ChatGPT workspaces;
- environment-backed token alternatives;
- deployed Actor schema and pricing inspection with `fetch-actor-details`;
- the current Actor tool and run/storage helper workflow;
- structured `RUN-SUMMARY` handling with one bounded same-input retry;
- bounded input and prompt examples;
- explicit empty-result and failure behavior;
- an offline validator and credential-safe live smoke script;
- the current live-validation boundary for the deployed Actor.

Use only the scoped hosted endpoint:

```text
https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/linkedin-enrich-translate-normalize-scraper
```

Start with OAuth and follow the complete
[MCP v1 instructions](../integrations/mcp/README.md).

## EURAXESS boundary

EURAXESS has a separate repository skill and compatibility endpoint:

```text
https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/euraxess-enrich-translate-normalize-scraper
```

Read the skill's
[client setup](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/client-setup.md)
before use. Its local `1.0` contract is unreleased and incompatible with the
known private older `0.5.1` deployment. Do not reuse the LinkedIn input,
LinkedIn run-summary retry policy, or destination live-validation claims for
EURAXESS.
