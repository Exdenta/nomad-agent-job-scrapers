# Codex and Claude MCP setup for EURAXESS

Installing this skill adds contract instructions and offline parsers.
Connecting MCP adds authenticated live tools. Neither step exposes a private
Actor to an unauthorized account or deploys the local `1.0` rewrite.

The Actor currently deployed under this name is a private older `0.5.1`
version. Do not execute it with this skill's strict `1.0` input. First fetch
Actor details and require a compatible schema.

Candidate scoped endpoint:

```text
https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/euraxess-enrich-translate-normalize-scraper
```

Hosted Streamable HTTP with OAuth is preferred. If policy requires an Apify
token, keep it in the client's environment or secret mechanism. Never place
the value in a skill, prompt, repository, or Actor input.

## Codex

```toml
[mcp_servers.apify]
url = "https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/euraxess-enrich-translate-normalize-scraper"
```

Then authenticate and verify:

```bash
codex mcp login apify
codex mcp list
```

Invoke the installed skill with:

```text
$euraxess-enrich-translate-normalize-scraper
```

## Claude Code

```bash
claude mcp add --transport http --scope project apify \
  "https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/euraxess-enrich-translate-normalize-scraper"
claude mcp list
```

Open `/mcp`, complete OAuth, and invoke:

```text
/euraxess-enrich-translate-normalize-scraper
```

Project scope writes only the non-secret URL. Every user completes OAuth for
their own Apify account. Use local or user scope only when that visibility is
intentional.

## Verification boundary

1. Confirm the server is connected and the account may access the exact Actor.
2. Fetch Actor details, pricing, build/version, and input schema.
3. Require `nomad-agent-job-search-input-v1` plus the closed EURAXESS
   extension. Stop on the known older schema.
4. Only after a compatible build exists, run a bounded `maxItems: 5` search
   with dedupe, translation, enrichment, and analytics disabled.
5. Poll to terminal and read `RUN-SUMMARY` when the run exposes a default
   key-value store. Retrieve a dataset only after `SUCCEEDED`; never present a
   failed run's partial rows as success.
6. Validate every successful row as `nomad-agent-job-v1` with
   `identity.source` equal to `euraxess` and the versioned EURAXESS custom
   extension.

No live-compatible EURAXESS `1.0` MCP run is claimed by this repository yet.
