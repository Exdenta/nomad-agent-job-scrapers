# MCP v1: LinkedIn normalized job search

Connect one Apify Actor to an MCP client, inspect its deployed contract and
pricing, run bounded LinkedIn searches, and retrieve the canonical
`nomad-agent-job-v1` records without exposing the rest of your Apify tool
catalog.

Use this scoped Streamable HTTP endpoint:

```text
https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/linkedin-enrich-translate-normalize-scraper
```

OAuth is the recommended authentication method. The tracked examples contain
no credential. Token alternatives reference the `APIFY_TOKEN` environment
variable; they never embed its value.

## Current validation boundary

On 2026-08-10 the two-tool scoped hosted endpoint was live-tested with bearer
authentication:

- MCP initialization negotiated protocol `2025-06-18`;
- `fetch-actor-details`, the scoped Actor tool, and the four automatically
  injected run/storage helpers were discovered;
- a bounded Actor call was accepted by MCP and created an Apify run;
- the deployed Actor then failed during `Actor.__aenter__` because its pinned
  Apify Python SDK `2.7.3` rejects the platform's newer `meta.origin = "MCP"`.

A narrow, version-scoped compatibility fix and focused tests are prepared in
the Actor source, but this integration repository does not deploy Actor code.
Do not describe the Actor-call path as end-to-end live-validated until that fix
is deployed and the `--run` smoke test below reaches `SUCCEEDED`.

Tool discovery and client configuration are valid today. The temporary Actor
runtime failure is not an OAuth, MCP transport, or input-schema error.

## What MCP exposes

The explicit metadata tool is:

```text
fetch-actor-details
```

Use it before the first paid run, and again whenever the deployed Actor may
have changed. It returns the deployed input schema, output information, and
current pricing; these live details take precedence over copied examples or
repository documentation. Pass the exact Actor name
`nomad-agent/linkedin-enrich-translate-normalize-scraper`.

The Actor selector currently produces this run tool:

```text
nomad-agent--linkedin-enrich-translate-normalize-scraper
```

Apify also injects the helpers needed for a long-running call:

```text
get-actor-run
get-dataset-items
get-key-value-store-record
abort-actor-run
```

The Actor tool returns run metadata, not dataset rows. If its status is still
`RUNNING`, follow `nextStep` and poll `get-actor-run`. After `SUCCEEDED`, pass
`storages.datasets.default.id` to `get-dataset-items`. Do not depend on a
`get-actor-output` tool: it was not present in the live scoped tool set.

## Client setup

### Codex CLI, Codex IDE, and ChatGPT desktop on a Codex host

Copy [`configs/codex.oauth.toml`](configs/codex.oauth.toml) into either
`~/.codex/config.toml` or a trusted project's `.codex/config.toml`. Then run:

```bash
codex mcp login apify_linkedin_jobs
codex mcp list
```

Codex CLI, the Codex IDE extension, and the ChatGPT desktop app share the MCP
configuration on the same Codex host. In the desktop or IDE UI, the equivalent
setup is **Settings -> MCP servers -> Add server**, choose **Streamable HTTP**,
paste the scoped URL, restart, and authenticate.

For non-interactive environments, copy
[`configs/codex.token.toml`](configs/codex.token.toml) and make
`APIFY_TOKEN` available to the Codex process. `bearer_token_env_var` reads the
value at runtime, so the token does not enter TOML or Git.

### Claude Code

The simplest OAuth setup is:

```bash
claude mcp add --transport http --scope user apify-linkedin-jobs \
  "https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/linkedin-enrich-translate-normalize-scraper"
```

Run `/mcp` inside Claude Code and complete the Apify browser authorization.
For a project-shared definition, copy
[`configs/claude-code.oauth.json`](configs/claude-code.oauth.json) to
`.mcp.json`; Claude Code requires `"type": "http"` on URL-based entries and
asks users to approve a project-scoped server.

The token alternative in
[`configs/claude-code.token.json`](configs/claude-code.token.json) uses
Claude Code's `${APIFY_TOKEN}` expansion in HTTP headers. Set the variable in
the environment that starts Claude Code. Do not run a shell command that
expands the token and then stores the expanded header in tracked JSON.

### Cursor

Copy [`configs/cursor.oauth.json`](configs/cursor.oauth.json) to either:

- `.cursor/mcp.json` for one project; or
- `~/.cursor/mcp.json` for the current user.

Cursor supports Streamable HTTP and should open the Apify OAuth flow when the
server first connects. If OAuth is unavailable in the current environment,
[`configs/cursor.token.json`](configs/cursor.token.json) uses Cursor's
`${env:APIFY_TOKEN}` header interpolation without storing the token.

### ChatGPT web

Local Codex, Claude, or Cursor configuration does not configure ChatGPT web.
The hosted Apify endpoint must be added as a custom MCP app:

1. An eligible workspace admin enables developer mode.
2. Open **Settings -> Apps -> Create** (labels can vary during the beta).
3. Enter the scoped URL at the top of this page.
4. Choose OAuth, select **Scan tools**, and authorize Apify.
5. Test the draft app in a new chat before publishing it to the workspace.

Because this app starts paid Actor runs, it needs full MCP action support.
OpenAI currently documents full MCP for Business, Enterprise, and Edu; Pro's
read/fetch-only custom-app access is not sufficient for this Actor tool. Custom
MCP apps are web-only and subject to workspace admin controls.

## First bounded search

Use this prompt from [`examples/prompts.md`](examples/prompts.md):

```text
Use fetch-actor-details for
nomad-agent/linkedin-enrich-translate-normalize-scraper first. Confirm its
deployed input schema and current pricing, then use only its configured Actor
tool. Search for at most 5 remote or hybrid TypeScript developer jobs in Spain
posted in the last 7 days. Disable translation, AI enrichment, analytics, raw
descriptions, and cross-run deduplication.

If the Actor is still running, follow nextStep with get-actor-run until it is
terminal. Only after SUCCEEDED, fetch up to 5 rows from the default dataset
with get-dataset-items. Validate that every row is nomad-agent-job-v1 with
exactly schemaVersion, identity, data, custom, llm, and raw at the top level.
If the successful dataset is empty, report "no matching jobs" without making
up a row or silently broadening the search.
```

The corresponding MCP tool arguments are in
[`examples/linkedin-search.mcp.json`](examples/linkedin-search.mcp.json).
`waitSecs` belongs to the Apify MCP wrapper, not the Actor's public input
contract. `0` starts the run without waiting; the client then polls explicitly.

## Result and error behavior

- `RUNNING`, `READY`, `TIMING-OUT`, and `ABORTING` are non-terminal. Follow
  `nextStep`; do not fetch the dataset as if it were final.
- `SUCCEEDED` with `itemCount: 0` is a valid empty search. It can mean no live
  matches or, when deliberately enabled, cross-run dedupe suppression.
- `FAILED`, `TIMED-OUT`, and `ABORTED` are errors. Report the run ID, status,
  status message, and exit code. Do not return a partial dataset as success.
- The narrow MCP URL does not include `get-actor-log`. Inspect the run in Apify
  Console or use `apify runs log RUN_ID` when deeper diagnostics are required.
- Retrieve rows with `get-dataset-items` and paginate when requesting more than
  one page. A tool response preview is not a durable copy of the dataset.
- Every canonical row must have exactly these roots:
  `custom`, `data`, `identity`, `llm`, `raw`, `schemaVersion`.
- `raw: null` is correct when `includeRaw` is false. Preserve `null` as unknown
  and `[]` as source-established empty; do not infer values from prose.

## Deterministic validation

Offline validation checks every tracked client config, the bounded example,
the scoped URL, secret placeholders, and the six-root result policy:

```bash
python3 integrations/mcp/scripts/validate_pack.py
python3 -m unittest tests.test_mcp_pack -v
```

Live discovery (no Actor run) requires an Apify token in the process
environment:

```bash
APIFY_TOKEN="$(apify auth token)" \
  python3 integrations/mcp/scripts/smoke_test.py
```

After the Actor compatibility fix is deployed, run the bounded end-to-end path:

```bash
APIFY_TOKEN="$(apify auth token)" \
  python3 integrations/mcp/scripts/smoke_test.py --run
```

The script never prints the token. It calls at most one Actor run, polls a
bounded number of times, and fetches at most five dataset rows.

## Primary documentation

- [Apify MCP server](https://docs.apify.com/integrations/mcp)
- [Apify MCP CLI install reference](https://docs.apify.com/cli/docs/reference#apify-mcp-install)
- [Apify ChatGPT integration](https://docs.apify.com/integrations/chatgpt)
- [Codex MCP configuration](https://developers.openai.com/codex/mcp/)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference/)
- [Claude Code MCP reference](https://code.claude.com/docs/en/mcp)
- [Cursor MCP reference](https://cursor.com/docs/mcp)
- [OpenAI developer mode and MCP apps](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt)
