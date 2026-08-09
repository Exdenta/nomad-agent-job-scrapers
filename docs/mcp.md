# MCP quickstart

The maintained MCP v1 pack is
[`integrations/mcp/README.md`](../integrations/mcp/README.md). It contains:

- credential-free OAuth setup for Codex, Claude Code, Cursor, and eligible
  ChatGPT workspaces;
- environment-backed token alternatives;
- deployed Actor schema and pricing inspection with `fetch-actor-details`;
- the current Actor tool and run/storage helper workflow;
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
