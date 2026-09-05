# Codex and Claude MCP setup for EURAXESS

Installing this skill adds contract instructions and offline parsers.
Connecting MCP adds authenticated live tools. Neither step changes Actor
availability or deploys code.

Use generic
`call-actor` with exact `callOptions.build: "1.0.28"` and verify the same build
number on the authoritative run; do not rely on either mutable tag.

Scoped endpoint:

```text
https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

Hosted Streamable HTTP with OAuth is preferred. If policy requires an Apify
token, keep it in the client's environment or secret mechanism. Never place
the value in a skill, prompt, repository, or Actor input.

## Codex

```toml
[mcp_servers.apify]
url = "https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record"
default_tools_approval_mode = "prompt"
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
  "https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record"
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
2. Fetch Actor details and pricing; verify the deployed schema before calling.
3. Call generic `call-actor` with the canonical Actor name, strict v1 input,
   `callOptions.build: "1.0.28"`, `callOptions.maxItems: 5`, and a conservative
   `callOptions.maxTotalChargeUsd`.
4. Require the run response to report `buildNumber: "1.0.28"` and stop on any
   mismatch.
5. Keep dedupe, translation, enrichment, and analytics disabled for the first
   bounded run.
6. Poll to terminal. If MCP omits `buildNumber`, verify the same run through
   Apify's authenticated run API. After exact-build `SUCCEEDED` with exit code
   0, read and validate `nomad-agent-run-summary-v4`.
7. If a usable `partial` result recommends a retry, wait the bounded timing and
   repeat the exact request at most once. Then retrieve the selected default
   dataset, reconcile its row count with `delivered`, and validate every row as `nomad-agent-job-v1` with
   `identity.source` equal to `euraxess` and the versioned EURAXESS custom
   extension.
8. Missing or invalid status stops delivery. Failed, timed-out, and aborted
   Apify runs are never retried from `RUN-SUMMARY`.

The repository records live and offline verification separately; a successful
older run is not proof that a newly edited integration is live-compatible.
