# Supported integration packs

This repository provides client-ready integration assets for the normalized
LinkedIn and EURAXESS job Actors and the distinct AI Job Search & Fit Scorer.
The source Actors emit `nomad-agent-job-v1`; the scorer emits candidate-specific
`nomad-ai-job-fit-v1` evaluations and must not be treated as a third source
flavor of the same row.

## Available packs

| Pack | Customer outcome | Setup guide |
| --- | --- | --- |
| n8n | Run a bounded source search or fit evaluation, then upsert the matching flat projection into Google Sheets; a separate LinkedIn starter sends new-job alerts | [n8n](../integrations/n8n/README.md) |
| Make | Process completed LinkedIn, EURAXESS, or fit-scorer Tasks and upsert the matching projection into Google Sheets | [Make](../integrations/make/README.md) |
| Airtable | Store the shared flat projection using `jobKey` for idempotency | [Airtable](../integrations/airtable/README.md) |
| MCP | Search or score through supported MCP clients with an exact build and cost cap | [MCP](../integrations/mcp/README.md) |
| REST API and webhooks | Run searches or scoring from custom applications and process exact-run completion events safely | [API and webhooks](../integrations/api/README.md) |
| Zapier | Build a scheduled fit-scorer-to-Sheets Zap from a tested editor specification | [Zapier](../integrations/zapier/README.md) |
| Agent Skills | Install source-specific guidance, validators, and parsers | [Agent Skills](agent-skills.md) |

Source-job packs preserve `nomad-agent-job-v1` as the canonical dataset contract.
Table destinations use the documented `nomad-agent-flat-job-v1` projection;
they do not replace the canonical record. `null` means unknown or unavailable,
while `[]` means the source established that the collection is empty.

Fit-scoring packs instead preserve `nomad-ai-job-fit-v1` and use the separate
`nomad-ai-job-fit-destination-v1` projection keyed by `matchKey`. Airtable is a
source-job destination only; the Zapier starter is fit-scorer specific.

## Compatibility

See the [compatibility matrix](integration-compatibility.md) for supported
Actor builds, input coverage, output handling, and the current validation
status of each pack.

The repository integration-tested pins are LinkedIn `1.0.2`, EURAXESS
`1.0.16`, and scorer `latest`. They are compatibility boundaries, not an
automatic statement that a source pin is the current Store default. Public
product and setup pages live at `https://nomadagent.dev/actors` and
`https://nomadagent.dev/integrations`.

Templates never include credentials or activate schedules when imported.
Start with the bounded examples, keep optional paid features disabled until
the base flow succeeds, and store credentials in the destination platform's
secret or connection manager.

An importable file, offline test, successful Actor run, hosted workflow,
named-destination write, marketplace submission, and public listing are
separate evidence states. The copy-ready n8n and Make listing drafts remain
unsubmitted until a hosted import and named disposable destination have been
proved.
