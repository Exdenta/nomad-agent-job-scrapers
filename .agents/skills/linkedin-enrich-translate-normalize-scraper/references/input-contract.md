# LinkedIn Actor input contract

Expected contract: `nomad-agent-job-search-input-v1`. Inspect the deployed
Actor tool schema before a paid run and stop if it does not match this
reference.

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `schemaVersion` | string | required | Must be `nomad-agent-job-search-input-v1` |
| `keyword` | string | empty | Role, skill, or title |
| `location` | string | empty | City, region, country, or broad geography |
| `linkedinSearch` | object | omitted | Versioned bounded multi-search plan |
| `strictGeography` | object | omitted | Source-only correlated country/region/city enforcement |
| `postedWithin` | enum | `24h` | `1h`, `24h`, `7d`, `30d`, or `any` |
| `workArrangements` | string array | omitted | Any union of `remote`, `hybrid`, `onsite` |
| `filters` | object | omitted | Versioned normalized-field expression |
| `companyProfileEnrichment` | boolean | `false` | Retrieve bounded public profiles linked by selected jobs |
| `companyFilters` | object | omitted | Versioned public-company-fact expression; requires company profile enrichment |
| `maxItems` | integer | `100` | Use 5 for exploratory runs; 0 requests the bounded 200-item window |
| `translateToEnglish` | boolean | `false` | Managed optional translation; no customer provider key required |
| `aiEnrichment` | object | `{"enabled": false, "accuracy": "silver"}` | Managed optional enrichment; Silver is the default tier and Gold is optional |
| `includeRaw` | boolean | `true` | False returns top-level `raw: null` |
| `dedupe` | object | `{"enabled": true, "key": ""}` | Optional cross-run delivery ledger; disable explicitly for one-off runs |
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

## Strict geography

Use `nomad-agent-linkedin-strict-geography-v1` only when physical geography
must be proven from the same normalized source location. Configure any of
uppercase ISO-2 `countries`, exact case-insensitive `regions`, and exact
case-insensitive `cities`, plus `unknownPolicy: "exclude"` or `"abort"`.
Description prose and LLM-filled locations are never accepted as geographic
evidence. Do not infer on-site work from a matching city or country.

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

Use only paths and operators accepted by the deployed tool schema. Filters
evaluate source-language values.

In supported build `0.6.45`, `translateToEnglish` covers title, classifications,
domains, applicant-requirement prose, benefits, eligibility and selection
text, work authorization, security clearance, and location preference. It
does not rewrite company or place names, identifiers, URLs, source-raw labels,
skills, qualifications, certifications, programme names, raw descriptions or
HTML, or LLM provenance. Verify the deployed Actor schema/build before relying
on the expanded fields.

## Public company profiles and filters

`companyProfileEnrichment: true` fetches a bounded set of public LinkedIn
company pages already linked by selected jobs. It uses no caller login cookie
or arbitrary URL and may leave the source-specific company extension `null`
when a profile is unavailable or unverified.

`companyFilters` requires enrichment and the discriminator
`nomad-agent-linkedin-company-filter-v1`. Filter only the allowlisted typed
public profile facts exposed by the deployed schema. Choose
`unknownPolicy: "exclude"` or `"abort"`; never turn an unavailable company
profile into a guessed match.

## Cross-run dedupe

Storage-free one-off input:

```json
{
  "enabled": false,
  "key": ""
}
```

When enabled, state is scoped by Actor, Apify user, and the explicit or derived
dedupe key. A stable opaque alert/profile key intentionally shares delivery
history across searches for that profile. Do not use a global account-wide key
for unrelated users or alerts.

To intentionally redeliver an old result set, use a new explicit dedupe key.
Retired replay fields are rejected by the closed input contract.
