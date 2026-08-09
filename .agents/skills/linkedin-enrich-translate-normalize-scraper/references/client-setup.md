# Codex and Claude MCP setup

The skill and the MCP connection are independent. Installing the skill adds
workflow instructions and local parsers. Connecting MCP adds authenticated
live tools. Neither step should copy a credential into the skill or repository.

Use this scoped hosted endpoint:

```text
https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/linkedin-enrich-translate-normalize-scraper
```

Hosted Streamable HTTP with OAuth is the default. Running Actors and reading
their datasets requires authentication. If organizational policy requires an
Apify token, keep it in the client's secret or environment mechanism; never
place its value in `SKILL.md`, a prompt, source control, or Actor input.

## Codex

Repository skills live at `.agents/skills/<skill-name>`. Personal skills live
at `$HOME/.agents/skills/<skill-name>`.

Configure the hosted MCP server in `$HOME/.codex/config.toml`, or in a trusted
project's `.codex/config.toml`:

```toml
[mcp_servers.apify]
url = "https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/linkedin-enrich-translate-normalize-scraper"
```

Then run:

```bash
codex mcp login apify
codex mcp list
```

Complete Apify OAuth in the browser. Restart the Codex client if a newly added
skill or MCP server is not visible, then invoke:

```text
$linkedin-enrich-translate-normalize-scraper
```

## Claude Code

Project skills live at `.claude/skills/<skill-name>`. Personal skills live at
`$HOME/.claude/skills/<skill-name>`.

For a shareable project configuration, add the hosted server with project
scope. This writes the non-secret URL to the project's `.mcp.json`; every user
still completes OAuth for their own Apify account:

```bash
claude mcp add --transport http --scope project apify \
  "https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/linkedin-enrich-translate-normalize-scraper"
claude mcp list
```

Open Claude Code and run `/mcp` to complete Apify OAuth and verify that the
server is connected. Invoke the installed skill with:

```text
/linkedin-enrich-translate-normalize-scraper
```

Use `--scope local` (the default) instead when the server definition should
stay private to the current project in `$HOME/.claude.json`. Use `--scope user`
only when it should be available across all local projects. Project-scoped MCP
configuration is shareable, but must contain only the URL, never an
authorization header with a real token.

## Verification boundary

1. Confirm the `apify` server is connected.
2. Confirm `fetch-actor-details`, the exact Actor tool, `get-actor-run`, and
   `get-dataset-items` are available.
3. Fetch the deployed Actor details, pricing, and input schema before a
   paid run.
4. Run a bounded `maxItems: 5` search with translation, AI enrichment,
   analytics, and cross-run dedupe disabled.
5. Poll non-terminal runs with `get-actor-run`. Only after `SUCCEEDED`, pass
   `storages.datasets.default.id` to `get-dataset-items` and paginate as
   needed.
6. Accept `SUCCEEDED` with zero items as a valid empty result. Treat `FAILED`,
   `TIMED-OUT`, and `ABORTED` as errors and never present partial data as
   success.

If the deployed schema differs from the skill, stop before execution and show
the mismatch. Installing the skill is not proof that the Actor or MCP server is
deployed, connected, authorized, or compatible.

## Official references

- [OpenAI Codex skills](https://developers.openai.com/codex/skills)
- [OpenAI Codex MCP](https://developers.openai.com/codex/mcp)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [Apify MCP server](https://docs.apify.com/integrations/mcp)
