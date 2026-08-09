# LinkedIn Actor input contract

Expected contract: `nomad-agent-job-search-input-v1`. Inspect the deployed
Actor tool schema before a paid run and stop if it does not match this
reference.

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `schemaVersion` | string | required | Must be `nomad-agent-job-search-input-v1` |
| `keyword` | string | empty | Role, skill, or title |
| `location` | string | empty | City, region, country, or broad geography |
| `postedWithin` | enum | `30d` | `1h`, `24h`, `7d`, `30d`, or `any` |
| `workArrangements` | string array | omitted | Any union of `remote`, `hybrid`, `onsite` |
| `maxItems` | integer | Actor default | Use 5 for a first run; 0 requests the bounded 200-item window |
| `translateToEnglish` | boolean | `false` | Owner-managed, additional per-result charge |
| `aiEnrichment` | boolean | `false` | Owner-managed null-only extraction, additional charge |
| `includeRaw` | boolean | `true` | False returns top-level `raw: null` |
| `dedupe` | object | disabled | Optional cross-run delivery ledger |
| `filters` | object | omitted | Versioned normalized-field expression |
| `linkedinSearch` | object | omitted | Versioned bounded multi-search plan |
| `analyticsEnabled` | boolean | `false` | Explicit opt-in only |

## Multi-search

Use a single input to combine up to eight keyword/location partitions:

```json
{
  "schemaVersion": "nomad-agent-job-search-input-v1",
  "linkedinSearch": {
    "schemaVersion": "nomad-agent-linkedin-search-v1",
    "searches": [
      {"keyword": "frontend engineer", "location": "Spain"},
      {"keyword": "TypeScript developer", "location": "European Union"}
    ],
    "orderBy": "newest"
  },
  "postedWithin": "7d",
  "maxItems": 50
}
```

Do not combine non-empty top-level `keyword`/`location` with non-empty
`linkedinSearch.searches`.

## Filters

Filters use the separately versioned `nomad-agent-job-filter-v1` expression:

```json
{
  "schemaVersion": "nomad-agent-job-filter-v1",
  "expression": {
    "all": [
      {
        "field": "data.title",
        "operator": "not_contains",
        "value": "manager"
      },
      {
        "field": "data.employment.workArrangements",
        "operator": "overlaps",
        "value": ["remote", "hybrid"]
      }
    ]
  }
}
```

Use only paths and operators accepted by the deployed tool schema. Filters run
against source-language values before optional translation.

## Cross-run dedupe

Disabled default:

```json
{
  "enabled": false,
  "key": "",
  "stateResetAcknowledged": false
}
```

When enabled, state is scoped by Actor, Apify user, and the explicit or derived
dedupe key. A stable opaque alert/profile key intentionally shares delivery
history across searches for that profile. Do not use a global account-wide key
for unrelated users or alerts.

The current contract requires `stateResetAcknowledged: true` when enabling the
new transactional ledger because older delivery history is not migrated.
