# EURAXESS Actor input contract

Target contract: `nomad-agent-job-search-input-v1` with the optional closed
`nomad-agent-euraxess-search-v1` extension. The local `1.0` rewrite is
unreleased, while the private deployed Actor is an older `0.5.1` build. Inspect
the deployed schema and stop when it does not exactly match this reference.

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `schemaVersion` | string | required | Must be `nomad-agent-job-search-input-v1` |
| `keyword` | string | empty | Title, discipline, skill, or research term |
| `location` | string | empty | Case-insensitive match against location/country text on search cards |
| `euraxessSearch` | object | omitted | Separately versioned keyword-expansion extension |
| `postedWithin` | enum | `30d` | `24h`, `7d`, `30d`, or `any`; EURAXESS rejects `1h` |
| `workArrangements` | string array | omitted | Unique subset of `remote`, `hybrid`, `onsite`; unknown does not match |
| `maxItems` | integer | `100` | Use 5 first; `0` means the bounded 200-item window |
| `dedupe` | object | enabled | Cross-run delivery suppression; explicitly disable for one-off use |
| `filters` | object | omitted | Closed `nomad-agent-job-filter-v1` expression |
| `aiEnrichment` | object | disabled Silver | Owner-managed null-only description extraction |
| `translateToEnglish` | boolean | `false` | Owner-managed selected-field translation |
| `includeRaw` | boolean | `true` | False emits top-level `raw: null` after any requested enrichment |
| `analyticsEnabled` | boolean | `false` | Explicit privacy-preserving aggregate opt-in |

Unknown and retired fields fail validation. Caller-supplied proxy selection,
timeouts, retries, concurrency, cache lifetimes, provider models, and provider
keys are not part of this contract.

EURAXESS publishes posting dates as calendar dates (`YYYY-MM-DD`), without an
hour or timezone. Therefore this source cannot honestly establish whether a
posting falls within the preceding hour. Its source-specific input schema
rejects `postedWithin: "1h"`, even if another Actor using the shared canonical
input discriminator supports that value.

Freshness uses inclusive UTC calendar-date cutoffs, not elapsed durations. For
`24h`, the cutoff is the previous UTC date, so both the current and previous
UTC date match and a result may be older than 24 elapsed hours. `7d` and `30d`
subtract 7 or 30 calendar days from the current UTC date and also include the
cutoff date. `any` applies no publication-date cutoff.

## EURAXESS keyword expansion

```json
{
  "euraxessSearch": {
    "schemaVersion": "nomad-agent-euraxess-search-v1",
    "translateKeywords": true
  }
}
```

The original keyword is always retained. The owner-managed provider may add
faithful equivalents used across EURAXESS languages. Failure falls back to the
original keyword. This option must not add adjacent roles or disciplines.

## Normalized filters

Filters run on normalized, source-language facts before optional output
translation:

```json
{
  "schemaVersion": "nomad-agent-job-filter-v1",
  "expression": {
    "all": [
      {
        "field": "data.locations[].countryCode",
        "operator": "eq",
        "value": "DE"
      },
      {
        "field": "data.title",
        "operator": "not_contains",
        "value": "internship"
      }
    ]
  }
}
```

Use only paths and operators exposed by the deployed schema. An unknown rich
fact must not be treated as a proven early card mismatch.

## Enrichment and translation

Enrichment is a strict object, not a boolean:

```json
{
  "aiEnrichment": {
    "enabled": true,
    "accuracy": "silver"
  }
}
```

`accuracy` is `silver` or `gold`. Both profiles are owner-managed. They read
only the complete public plain-text description, fill allowlisted still-null
paths, and record provenance in `llm`. Provider failure preserves the base
record and records `llm.status: failed` for that row.

`translateToEnglish` runs after normalization, optional enrichment, and exact
filtering. It is limited to title, skills/qualifications, specific
requirements, benefits, eligibility criteria, and selection process. It does
not rewrite organisations, research domains, locations, URLs, identifiers,
raw descriptions/HTML, or LLM provenance.

## Cross-run dedupe

One-off, storage-free input:

```json
{
  "dedupe": {
    "enabled": false,
    "key": ""
  }
}
```

When enabled with an empty key, scope is derived from the Apify user and the
canonical search/filter input. A nonempty public opaque key intentionally
shares history for one alert/profile within that user. An optional nonempty
`replayEpoch` starts an intentional new delivery generation. Do not use one
global account-wide key for unrelated searches or users.

Availability observations are a separate evidence layer; they do not act as
the delivery ledger.
