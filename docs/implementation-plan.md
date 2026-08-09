# Implementation plan

All five packs share one input contract, one canonical output, and one flat
projection. Build and test that shared layer once before duplicating mappings
inside automation platforms.

## Shared foundation

Already scaffolded:

- scoped Apify MCP configuration;
- LinkedIn Agent Skill for Codex and Claude;
- strict six-root output validator;
- `nomad-agent-flat-job-v1` mapper and JSON Schema;
- offline tests and a synthetic fixture.

Release gates:

1. Test the local Actor `0.6` build without deploying it.
2. Explicitly authorize and deploy the Actor.
3. Confirm that the hosted MCP server exposes the deployed input and inferred
   output schema.
4. Run a bounded live search and validate the complete dataset.
5. Remove the repository's pre-release notice only after those checks pass.

## Pack 1: n8n

Deliverables:

- importable workflow JSON;
- environment/credential setup guide;
- scheduled and manual triggers;
- Actor run plus complete dataset retrieval;
- flat projection in a Code node;
- duplicate lookup/upsert on `jobKey`;
- Google Sheets append/update;
- Telegram notification path and an email alternative;
- partial-failure and rerun behavior.

Needed for an offline template: chosen default notification path and an example
Sheet column order. Needed for end-to-end proof: a disposable n8n instance,
Apify connection, Google account, and Telegram bot or SMTP account.

## Pack 2: Make

Deliverables:

- importable scenario blueprint;
- completed-Actor-run trigger/webhook;
- paginated dataset retrieval;
- flat mapping;
- Airtable + Slack default route;
- documented substitutions for Google Sheets + email;
- error handler and idempotent rerun behavior.

Needed for an offline blueprint: chosen default route. Needed for proof: a Make
workspace and disposable Apify, Airtable/Google, and Slack/email connections.
Connection IDs and secrets will never be committed.

## Pack 3: Airtable

Deliverables:

- base/table field specification;
- CSV header/template or Base schema instructions;
- formula/view for duplicate visibility;
- lookup-then-create/update recipes for n8n and Make;
- field-size guidance for descriptions and optional canonical JSON.

Use `jobKey` as the cross-source unique key. For a LinkedIn-only table,
`identityExternalId` is also safe for duplicate lookup, but `jobKey` makes the
base reusable when more job Actors are added.

Needed for proof: a disposable Airtable base and permission to create/delete
test rows.

## Pack 4: MCP

Initial implementation is present in [mcp.md](mcp.md) and the repository Agent
Skill. Remaining work is live validation after Actor deployment:

- Codex OAuth and bounded run;
- Claude Code OAuth and bounded run;
- Cursor OAuth and bounded run;
- ChatGPT custom App tool scan and bounded run where plan/admin access permits;
- full-output retrieval and schema validation in every client.

Needed for proof: Apify OAuth access and the listed clients. ChatGPT testing
also needs a plan/workspace role that permits custom MCP Apps.

## Pack 5: API and webhook

Deliverables:

- synchronous curl, Python, JavaScript, and TypeScript examples;
- asynchronous run + poll + paginated dataset examples;
- completed-run webhook receiver example;
- idempotent database upsert keyed by `jobKey`;
- retry, timeout, pagination, and rate-limit guidance;
- example PostgreSQL table plus generic webhook payload contract;
- verification of webhook authenticity using the mechanism supported by the
  current Apify webhook API.

Needed for offline examples: preferred primary runtime (recommend TypeScript
plus Python parity) and database example (recommend PostgreSQL). Needed for
live proof: a temporary HTTPS receiver and a disposable database.

## Repository decisions before publication

Recommended defaults:

| Decision | Recommendation |
| --- | --- |
| GitHub owner/name | `Exdenta/nomad-agent-job-scrapers` |
| Display name | Nomad Agent Job Scrapers |
| Visibility | Public |
| License | MIT for unrestricted reuse, including commercial use |
| Primary API examples | TypeScript and Python |
| n8n default | Google Sheets + Telegram, with email variant |
| Make default | Airtable + Slack, with Sheets/email substitutions |

The repository can be published after the owner, visibility, and license are
confirmed and GitHub CLI authentication is restored.
