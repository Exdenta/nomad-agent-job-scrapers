# Job contracts

## Canonical record

`nomad-agent-job-v1` has exactly six top-level keys:

| Root | Meaning |
| --- | --- |
| `schemaVersion` | Contract discriminator |
| `identity` | Source, source-owned external ID, and canonical posting URL |
| `data` | Normalized job facts |
| `custom` | Versioned board-specific extension, or `null` |
| `llm` | Enrichment status and provenance, not a second facts object |
| `raw` | Complete source description text/HTML, or `null` |

Static source values win. Optional LLM enrichment may fill only fields that
remain `null`. Consumers must preserve `null` (unknown) versus `[]` (explicitly
empty).

See the skill's [output reference](../.agents/skills/linkedin-enrich-translate-normalize-scraper/references/output-contract.md)
for the fields used by the LinkedIn Actor.

## Flat integration projection

`nomad-agent-flat-job-v1` is a table-oriented, derived view. Its schema is
[`integrations/shared/flat-job-v1.schema.json`](../integrations/shared/flat-job-v1.schema.json).

Important rules:

- `jobKey` is `source:externalId`; if the source ID is absent, the canonical URL
  is used as a fallback.
- Array values are compact JSON strings. This keeps `null`, `[]`, and a
  populated array distinguishable in JSON-capable destinations.
- `locationText` is a display string and is not a normalized geographic key.
- `descriptionText` is omitted when the Actor was run with `includeRaw: false`.
- The projection intentionally omits deep requirements and provenance fields.
  Store the canonical dataset as the system of record when those matter.

Generate the projection with:

```bash
python3 .agents/skills/linkedin-enrich-translate-normalize-scraper/scripts/flatten_output.py \
  actor-output.json --output flat-output.json
```
