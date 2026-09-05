# Y Combinator startup jobs for pipelines and alerts

Use [the normalized YC Actor](https://apify.com/nomad-agent/ycombinator-enrich-translate-normalize-scraper) for
startup recruiting pipelines, job boards, and recurring alerts. It returns
`nomad-agent-job-v1` with `identity.source = ycombinator_was`, keeping stable
job identity across source integrations. The legacy flat-export Actor remains
separate; this guide covers only the normalized service.

## Start with five jobs

```json
{
  "schemaVersion": "nomad-agent-job-search-input-v1",
  "firstRunMode": false,
  "postedWithin": "any",
  "maxItems": 5,
  "dedupe": {
    "enabled": false,
    "key": ""
  },
  "aiEnrichment": {
    "enabled": false,
    "accuracy": "silver"
  },
  "translateToEnglish": false,
  "includeRaw": true,
  "analyticsEnabled": false
}
```

The base event price is $0.0009 per result ($0.90 per 1,000), checked
2026-09-05. Five base results cost $0.0045 in Actor events. Optional Silver
adds $0.006 per qualifying job, Gold $0.010, and translation $0.006.
100 base results plus Silver on all 100 cost $0.69 in Actor events.
Confirm current Store pricing and your plan before a run. `firstRunMode: true`
selects paid Silver enrichment and translation; the recipe above leaves it off.

## Search and source limits

The Actor filters a regularly refreshed inventory of complete public postings;
it does not scrape YC pages on demand. Unavailable or stale inventory fails
closed. Availability evidence is a dated observation, not proof that a job is
still accepting applicants. This service is unaffiliated with Y Combinator.

- `keyword` searches cached content; `location` matches the published label.
- `postedWithin` defaults to `any`; `1h`, `24h`, `7d`, and `30d` use the first
  observation hour, not the employer's posting date. `orderBy` accepts
  `newest` or `oldest` using that timestamp.
- `workArrangements` accepts `remote`, `hybrid`, and `onsite`. Unknown modes do
  not match. A city label is not evidence of onsite work, so onsite and hybrid
  searches can return very few matches.
- `maxItems` accepts 0–1,000; zero means the bounded 1,000-result window.
- `dedupe` accepts `enabled` and `key`. Use a stable named key for a recurring
  alert. The empty default key uses the default delivery scope.
- `filters` uses the shared [normalized filter grammar](https://github.com/Exdenta/nomad-agent-job-scrapers/blob/main/.agents/skills/linkedin-enrich-translate-normalize-scraper/references/input-contract.md#filters).
- `aiEnrichment` accepts `enabled` and `accuracy` (`silver` or `gold`). It fills
  only still-missing description-backed fields. `translateToEnglish` affects
  selected display fields and is usually unnecessary for this English source.
- `includeRaw: false` returns `raw: null`; `analyticsEnabled` is optional.

Use multiple terms and source taxonomy filters like this:

```json
{
  "schemaVersion": "nomad-agent-job-search-input-v1",
  "postedWithin": "any",
  "maxItems": 5,
  "ycSearch": {
    "schemaVersion": "nomad-agent-ycombinator-search-v1",
    "queries": ["python", "founding engineer"],
    "companyBatches": ["S23", "W24"],
    "roleTypes": ["engineering"],
    "jobTypes": ["Full-time"]
  }
}
```

Queries are OR terms over one inventory; order does not change behavior. Do not
combine a non-empty `keyword` with non-empty `ycSearch.queries`. Batches are YC
cohorts. Role types match source category substrings; job types use source labels
and supported full-time, part-time, contract, and internship aliases.

## API and MCP

Use build selector `latest` and record the returned numeric build number and immutable `buildId`.
Historical build `1.0.6` (`6aqB3jicww58310qm`) has Actor
execution proof only; hosted MCP and named destination writes are separate.

```bash
curl --fail-with-body -X POST \
  'https://api.apify.com/v2/acts/nomad-agent~ycombinator-enrich-translate-normalize-scraper/runs?build=latest&maxTotalChargeUsd=0.05&timeout=600&memory=512' \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"schemaVersion":"nomad-agent-job-search-input-v1","postedWithin":"any","maxItems":5,"dedupe":{"enabled":false,"key":""},"firstRunMode":false,"aiEnrichment":{"enabled":false,"accuracy":"silver"},"translateToEnglish":false}'
```

Poll the returned run ID to terminal status. Read its `RUN-SUMMARY` and default
dataset; paginate until complete. Reconcile the count with `delivered` and
inspect `status`, `resultsLimited`, and `retry`. Never start another paid run
without an authorized retry budget. Honor at most one recommended retry with
the same input, exact build, item cap, and charge cap. Use `source:externalId` as the downstream
job key. Keep canonical rows when projecting into tables.

For MCP, connect the generic Apify tools:

```text
https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

Inspect current `call-actor` tool metadata, then pass the Actor identifier,
the bounded input above, and `callOptions` containing
`{"build":"latest","maxTotalChargeUsd":0.05,"maxItems":5}`.
Use `latest` and retain the returned run ID, numeric build number, and immutable build ID.

## Actor execution evidence

On 2026-09-05, run `mh2g0uwOuyNIMzKai` executed build `1.0.6`
(`6aqB3jicww58310qm`) and delivered five unique complete records. All five
passed canonical and YC v2 schema validation and carried the public schema URL.
The v4 summary reported `partial`, `resultsLimited: true`, and `delivered: 5`
because the input capped delivery at five; no retry was recommended. The run
charged five result events and zero enrichment or translation events. This is
a bounded Actor/API canary, not source-wide completeness or destination proof.

## Output and installation

Six roots: `schemaVersion`, `identity`, `data`, `custom`, `llm`, `raw`.
The [canonical schema](https://github.com/Exdenta/nomad-agent-job-scrapers/blob/main/integrations/shared/nomad-agent-job-v1.schema.json)
describes common fields; the [YC v2 schema](https://github.com/Exdenta/nomad-agent-job-scrapers/blob/main/integrations/shared/ycombinator-v2.schema.json)
validates `custom.data`. `null` means unknown, `[]` explicitly empty. A `$` salary
may have null currency and period; raw city text may have null parsed geography.
Founders are company context, not hiring contacts. Raw descriptions stay in the
source language even when selected fields are translated.

```bash
python3 scripts/install_skill.py --skill ycombinator-enrich-translate-normalize-scraper --client both --target /path/to/project
```

The [Agent Skill](https://github.com/Exdenta/nomad-agent-job-scrapers/blob/main/.agents/skills/ycombinator-enrich-translate-normalize-scraper/SKILL.md) supports source-specific
input and completion checks. Existing LinkedIn/EURAXESS destination templates
have not been ported or live-tested for this YC profile; do not merely replace
their Actor slug. See the [compatibility matrix](https://github.com/Exdenta/nomad-agent-job-scrapers/blob/main/docs/integration-compatibility.md).
