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

Actor `0.6` release state:

- local Actor tests passed;
- deployment was explicitly authorized and the verified build was promoted;
- a bounded production run returned a strict six-root normalized record;
- hosted MCP client-specific validation remains separate from Actor deployment.

## Pack 1: n8n

Deliverables:

- [x] importable workflow JSON;
- [x] environment/credential setup guide;
- [x] scheduled and manual triggers;
- [x] Actor run plus complete dataset retrieval;
- [x] flat projection in a Code node;
- [x] within-run duplicate suppression and Sheet upsert on `jobKey`;
- [x] Google Sheets append/update;
- [x] partial-failure and rerun behavior.

The basic importable pack and Sheet column order are offline tested. The Actor,
n8n Cloud, and Google Sheets path is also live-validated. Notifications and a
separate previously-delivered cache are intentionally outside this template.

## Pack 2: Make

Deliverables:

- [x] importable scenario blueprint JSON;
- [x] scheduled or manual Actor run with bounded smoke-test defaults;
- [x] dataset retrieval through Make's native Apify app;
- [x] strict six-root validation and 32-column flat mapping in Make Code;
- [x] Google Sheets lookup and append/update on `jobKey`;
- [x] sequential rerun behavior without a separate delivery cache;
- [x] connection, smoke-test, and scheduling instructions.

The basic pack is intentionally Google Sheets only. Slack, email, Airtable,
data stores, and a second advanced scenario are outside this template. The
blueprint and mappings are offline tested. Needed for live proof: a Make
workspace plus disposable Apify and Google connections. Connection IDs and
secrets will never be committed.

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
| n8n default | Basic Google Sheets append-or-update only |
| Make default | Basic Google Sheets upsert only |

The repository can be published after the owner, visibility, and license are
confirmed and GitHub CLI authentication is restored.
