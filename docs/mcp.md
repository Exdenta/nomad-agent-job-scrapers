# MCP quickstart

## What this provides

Apify's hosted MCP server exposes the LinkedIn Actor as an authenticated tool
to an AI client. The client can start a run, inspect the output preview, and
retrieve the complete dataset.

Use this least-privilege server URL:

```text
https://mcp.apify.com?tools=nomad-agent/linkedin-enrich-translate-normalize-scraper
```

This guide follows Apify's current Streamable HTTP and OAuth setup. Do not use
the deprecated SSE transport.

## Prerequisites

1. Create an Apify account.
2. Confirm that the Actor is available to your account.
3. Use OAuth when the client supports it. If a client needs a token, create it
   in Apify Console and keep it outside source control.
4. Until the repository's pre-release notice is removed, expect the public
   Actor and these `0.6` examples to differ.

## Codex

The shortest setup uses Apify CLI:

```bash
apify login
apify mcp install codex --tools nomad-agent/linkedin-enrich-translate-normalize-scraper
```

For a direct remote configuration, add this to `~/.codex/config.toml`:

```toml
[mcp_servers.apify]
url = "https://mcp.apify.com?tools=nomad-agent/linkedin-enrich-translate-normalize-scraper"
```

Then run `codex mcp login apify` and complete OAuth in the browser.

## Claude Code

Use Apify CLI:

```bash
apify login
apify mcp install claude-code --tools nomad-agent/linkedin-enrich-translate-normalize-scraper
```

Or add the HTTP server directly:

```bash
claude mcp add --transport http apify \
  "https://mcp.apify.com?tools=nomad-agent/linkedin-enrich-translate-normalize-scraper"
```

Run `/mcp` inside Claude Code if the OAuth authorization flow has not started.

## Cursor

Use `apify mcp install cursor --tools
nomad-agent/linkedin-enrich-translate-normalize-scraper`, or create
`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "apify": {
      "url": "https://mcp.apify.com?tools=nomad-agent/linkedin-enrich-translate-normalize-scraper"
    }
  }
}
```

Cursor should open the Apify OAuth flow when the server first connects.

## Claude Desktop

Open the connector settings, add a custom connector, and use the scoped server
URL from the top of this page. Complete Apify OAuth when prompted.

## ChatGPT

ChatGPT connects to remote MCP servers through custom Apps. Availability and
admin permissions vary by plan.

1. Enable developer mode in **Settings -> Apps -> Advanced settings**, or ask
   the workspace admin to enable custom MCP apps.
2. Choose **Create app**.
3. Enter the scoped Apify MCP URL from the top of this page.
4. Scan tools and complete Apify OAuth.
5. Test the draft app in a new chat before publishing it to a workspace.

ChatGPT cannot connect directly to a local-only MCP server. The hosted Apify
endpoint is already remote and is the appropriate option here.

## Recommended first prompt

```text
Use the configured LinkedIn normalized job-search Actor.

Search input:
- keyword: TypeScript developer
- location: Spain
- postedWithin: 7d
- workArrangements: remote and hybrid
- maxItems: 20
- translateToEnglish: false
- aiEnrichment: false
- includeRaw: false
- cross-run dedupe: disabled

Fetch the complete Actor output, not only the preview. Validate that every
item uses nomad-agent-job-v1 and has exactly schemaVersion, identity, data,
custom, llm, and raw at the top level. Summarize the jobs in a compact table,
but retain the canonical records.
```

Expected Actor input for the upcoming `0.6` contract:

```json
{
  "schemaVersion": "nomad-agent-job-search-input-v1",
  "keyword": "TypeScript developer",
  "location": "Spain",
  "postedWithin": "7d",
  "workArrangements": ["remote", "hybrid"],
  "maxItems": 20,
  "translateToEnglish": false,
  "aiEnrichment": false,
  "includeRaw": false,
  "dedupe": {
    "enabled": false,
    "key": "",
    "stateResetAcknowledged": false
  },
  "analyticsEnabled": false
}
```

## Tool behavior

- A client may expose the Actor as a named tool or through a generic Actor-call
  tool. Inspect the tool schema instead of guessing argument names.
- Actor calls may return only an output preview. Use Apify's automatically
  included `get-actor-output` tool with the returned dataset ID to fetch all
  requested items.
- Keep runs bounded while testing. Start with `maxItems: 5`.
- Do not enable translation or AI enrichment unless the user asks for them and
  accepts their extra cost.
- Cross-run dedupe is stateful. Enable it only for a deliberate alert/profile
  scope and follow the Actor input schema's reset acknowledgement.

## Troubleshooting

- **Tool missing:** reconnect the MCP server and verify the `tools=` value uses
  the exact Actor name.
- **Authentication error:** reconnect OAuth, or run `apify login` before the
  CLI installer. Never paste a token into a committed config file.
- **Input rejected:** fetch the deployed Actor details. The public build may
  not yet match the pre-release `0.6` examples in this repository.
- **Only a few results are visible:** retrieve the complete output with the
  dataset ID instead of relying on the tool preview.
- **Unexpected shape:** stop downstream writes and validate with the included
  parser before flattening.

## Primary references

- [Apify MCP server documentation](https://docs.apify.com/integrations/mcp)
- [OpenAI: developer mode and MCP apps in ChatGPT](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt)
- [Anthropic: connect Claude Code to tools via MCP](https://docs.anthropic.com/en/docs/claude-code/mcp)
