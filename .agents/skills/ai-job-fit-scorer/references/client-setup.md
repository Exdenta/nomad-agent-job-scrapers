# Client setup boundary

Installing this skill adds contract instructions and offline validators. It
neither connects Apify nor authorizes paid runs.

## Hosted MCP with OAuth

Use this five-tool server URL:

```text
https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

For Codex, add a project-scoped entry to `.codex/config.toml`:

```toml
[mcp_servers.apify_job_fit]
url = "https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record"
```

Open and trust the project, then run `codex mcp login apify_job_fit`.
For Claude Code, add the same URL as an HTTP server and authenticate in `/mcp`:

```bash
claude mcp add --transport http --scope project apify-job-fit \
  'https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record'
```

The Apify CLI's `apify mcp install` command uses the token saved by
`apify login` by default and can embed it in client configuration. It is not
an OAuth-only installation path. Prefer the credential-free URL above; never
paste a token into chat or commit one to a repository. If token authentication
is needed, configure an environment-backed bearer token in the client.

See the official [Apify MCP guide](https://docs.apify.com/integrations/mcp)
and [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

## Execute only after checking compatibility

Fetch Actor details and current account pricing before a paid run. Use generic
`call-actor` with build `latest`, item and total-charge caps. Inspect the tool's
advertised input schema: if it cannot forward build or charge caps, use the
REST API instead of silently dropping those controls. Fetch all dataset pages
from the run's default dataset and read its `RUN-SUMMARY` from the matching
key-value store. Installing or inspecting MCP does not prove an Actor call or
a destination write.

## Without MCP

Start a run with
`POST /v2/actors/nomad-agent~ai-job-fit-scorer/runs?build=latest&maxItems=5&maxTotalChargeUsd=0.10`,
poll `GET /v2/actor-runs/{runId}`, then fetch only that run's storages.
The [REST client](https://github.com/Exdenta/nomad-agent-job-scrapers/blob/main/integrations/api/ai-job-fit-scorer-run-and-fetch.mjs)
performs exact-run settlement checks. It does not configure a destination.
