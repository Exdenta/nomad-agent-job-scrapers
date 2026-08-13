# Supported integration packs

This repository provides client-ready integration assets for the normalized
LinkedIn and EURAXESS job Actors.

## Available packs

| Pack | Customer outcome | Setup guide |
| --- | --- | --- |
| n8n | Run a bounded search and upsert a flat job view into Google Sheets | [n8n](../integrations/n8n/README.md) |
| Make | Process completed Actor runs and upsert jobs into Google Sheets | [Make](../integrations/make/README.md) |
| Airtable | Store the shared flat projection using `jobKey` for idempotency | [Airtable](../integrations/airtable/README.md) |
| MCP | Search through supported MCP clients with an exact build and cost cap | [MCP](../integrations/mcp/README.md) |
| REST API and webhooks | Run searches from custom applications and process completion events safely | [API and webhooks](../integrations/api/README.md) |
| Agent Skills | Install source-specific guidance, validators, and parsers | [Agent Skills](agent-skills.md) |

All packs preserve `nomad-agent-job-v1` as the canonical dataset contract.
Table destinations use the documented `nomad-agent-flat-job-v1` projection;
they do not replace the canonical record. `null` means unknown or unavailable,
while `[]` means the source established that the collection is empty.

## Compatibility

See the [compatibility matrix](integration-compatibility.md) for supported
Actor builds, input coverage, output handling, and the current validation
status of each pack.

Templates never include credentials or activate schedules when imported.
Start with the bounded examples, keep optional paid features disabled until
the base flow succeeds, and store credentials in the destination platform's
secret or connection manager.
