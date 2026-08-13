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

See the source-specific output references for
[LinkedIn](../.agents/skills/linkedin-enrich-translate-normalize-scraper/references/output-contract.md)
and
[EURAXESS](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/output-contract.md).
LinkedIn uses `custom: null`; EURAXESS uses a separately versioned `custom`
extension and must not flatten its academic taxonomy into education facts.
The exact public mirror of the canonical extension is
[`integrations/shared/euraxess-v1.schema.json`](../integrations/shared/euraxess-v1.schema.json);
its canonical `$id` is intentionally unchanged.

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
python3 .agents/skills/euraxess-enrich-translate-normalize-scraper/scripts/flatten_output.py \
  actor-output.json --output flat-output.json
```

The same flat schema is reused by both skills, but the source validator is not
interchangeable. The EURAXESS mapper first requires `identity.source` equal to
`euraxess`, a named-person-only hiring-contact list, and the closed EURAXESS
v1 custom extension.

## Run completion

Delivery uses terminal Actor status, exact build identity, the canonical
minimal `nomad-agent-run-summary-v4` record under `RUN-SUMMARY`, and the
validated default dataset. Maintained integrations require the summary,
reconcile its `delivered` count with the dataset, and honor at most one atomic
bounded retry recommendation for a usable `partial` result. See the
[run-completion policy](retry-contract.md).

The JSON Schema documents the closed structural shape. Cross-field outcome and
atomic retry invariants must also pass:

```bash
python3 integrations/shared/validate_run_summary.py < run-summary.json
```
