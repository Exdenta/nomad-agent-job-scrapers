# Input contract (build 0.1.22)

The Actor input is a closed object: unknown top-level keys fail the run before
any paid work. This page lists every field, what the runtime does with it, and
the vocabulary the runtime accepts.

## Top level

| Field | Type | Meaning |
| --- | --- | --- |
| `mode` | `"search"` (default) or `"score-jobs"` | Search public sources, or score jobs you supply. |
| `search` | object | Search settings. Used only in `search` mode. |
| `jobs` | array of `nomad-agent-job-v1` | Inline supplied jobs, at most 200. `score-jobs` only. |
| `sourceDatasetId` | string | Immutable Apify dataset ID (not a name or URL) whose items are `nomad-agent-job-v1` records. `score-jobs` only. |
| `sourceActorRunId` | string | Exact upstream run ID; the run must be `SUCCEEDED` with exit code 0. Its default dataset is read. `score-jobs` only. |
| `expectedSourceBuild` | string | Optional guard for `sourceActorRunId`: build number or build ID that the upstream run must report. |
| `maxItems` | integer 1–200, default 25 | Maximum unique jobs evaluated. Caps the merged search result or the supplied source. |
| `candidateProfile` | object | Structured candidate facts (see below). |
| `resume` | string | URL of a text-based PDF or TXT uploaded through the Apify Console. Only Apify upload hosts are accepted. |
| `resumeText` | string | Plain résumé text, up to 8,000 readable characters. |
| `preferences` | string | Up to 4,000 characters of explicit constraints. Scoring only; never narrows the search. |
| `resultMode` | `"shortlist"` (default) or `"audit"` | What reaches the dataset and the meter. |
| `minDeliveryScore` | integer 0–5, default 2 | Inclusive shortlist threshold. Ignored for filtering in audit mode. |
| `minRankToForward` | integer 0–100, default 30 | Deterministic pre-screen rank below which a job is held before any AI call. |
| `maxAiItems` | integer 0–200, optional | Cap on AI verdict calls; the rest become `forward_cap_hold`. |
| `recoverHolds` | boolean, default false | Also send recoverable static holds to AI. |
| `aiConcurrency` | integer 1–8, default 4 | Concurrent AI verdict calls. |

Supply exactly one of `candidateProfile`, `resume`, or `resumeText` for a real candidate. A run
with none of them scores the built-in example candidate, caps evaluation at
three jobs, and marks `candidate.usedExampleProfile: true` in `RUN-SUMMARY`.
Never present such a run as the user's result.

In `score-jobs` mode exactly one of `jobs`, `sourceDatasetId`, or
`sourceActorRunId` must be set. Each supplied job needs the six top-level
fields `schemaVersion`, `identity`, `data`, `custom`, `llm`, and `raw`;
`identity` needs `source` plus `externalId` or `url`; `raw.description` holds
the posting text, at most 20,000 characters. Oversized evidence is rejected,
not truncated. A complete record is in
[`docs/examples/ai-job-fit-scorer/inline-input.json`](https://github.com/Exdenta/nomad-agent-job-scrapers/blob/main/docs/examples/ai-job-fit-scorer/inline-input.json).

## `search`

| Field | Type | Runtime behavior |
| --- | --- | --- |
| `sources` | array, 1–10 unique keys | Closed set: `linkedin`, `remote_boards`, `builtin`, `justjoinit`, `nofluffjobs`, `hackernews`, `ycombinator_was`, `wttj`, `infojobs`, `tecnoempleo`. Default: the first, second, and fourth. Unknown keys fail the run. |
| `keywords` | array of 1–10 strings, each ≤ 100 chars | Required. Built In and No Fluff Jobs use developer categories instead and report keyword support as unsupported. |
| `location` | string ≤ 200 chars | Native filter on LinkedIn, Just Join IT, InfoJobs, and Tecnoempleo. Other sources ignore it. |
| `countryCodes` | array of two-letter codes, ≤ 30 | Forwarded to Welcome to the Jungle only. Upper-cased. |
| `remoteOnly` | boolean, default false | Keeps only jobs explicitly normalized as fully remote; hybrid and unknown are dropped. |
| `titleExclude` | array of ≤ 20 strings | Title exclusion on LinkedIn, remote boards, Just Join IT, No Fluff Jobs, Y Combinator, InfoJobs, and Tecnoempleo. |
| `experienceLevels` | array of ≤ 12 strings | Just Join IT experience filter (for example `junior`, `mid`, `senior`). Others ignore it. |
| `maxExperienceYears` | integer 0–60 | Welcome to the Jungle only. |
| `postedWithinDays` | integer 0–365, default 7 in the Console form | Recency where a source exposes it. Y Combinator and Welcome to the Jungle do not; unknown dates are kept. |
| `maxItemsPerSource` | integer 1–50, default 10 | Full postings kept per source before merging and deduplication. |
| `cacheTtlSeconds` | integer 0–86400, default 1800 | Source HTTP response reuse window. `0` forces fresh requests. |
| `concurrency` | integer 1–10, default 3 | Concurrent source requests. |
| `sourceTimeoutSecs` | integer 30–300, default 120 | Per-source deadline. |

## `candidateProfile`

A closed object; unknown keys fail the run. At least one of `primaryRole`,
`targetTerms`, `skills`, or `freeText` is required.

| Field | Type | Rule |
| --- | --- | --- |
| `primaryRole` | string ≤ 200 | Current or primary role, when evidenced. |
| `targetTerms` | array ≤ 30 strings | Roles the candidate can credibly perform now. |
| `skills` | array ≤ 100 strings | Skills explicitly evidenced. |
| `seniorityLevels` | array ≤ 12 strings, each ≤ 40 | Recognized values: `intern`, `entry`, `junior`, `associate`, `mid`, `senior`, `lead`, `staff`, `principal`. Aliases such as `middle` or `entry-level` are normalized. |
| `yearsExperience` | number ≥ 0 | Total relevant years. |
| `workableLanguages` | array of `{language, level?, evidence}` | `language` and `evidence` are required per item. |
| `workableLanguagesComplete` | boolean | True only when the list is exhaustive. |
| `acceptedWorkArrangements` | array ⊆ {`remote`, `hybrid`, `onsite`}, ≤ 3 | Optional. When present it must equal the set of arrangements whose location list below is non-empty. |
| `remoteLocations` | array ≤ 30 strings | Regions from which remote work is accepted. |
| `hybridLocations` | array ≤ 30 strings | Cities where hybrid work is accepted. |
| `onsiteLocations` | array ≤ 30 strings | Cities where on-site work is accepted. |
| `workArrangementPreferencesComplete` | boolean | True only when the lists are exhaustive; cannot be true when every list is empty. |
| `acceptedCountryCodes` | array of two-letter codes | Explicitly accepted countries. |
| `acceptedContractTypes` | array ≤ 20 strings, each ≤ 80 | For example `permanent`, `fixed_term`, `contract`, `contractor`, `freelance`, `internship`. |
| `acceptedContractTypesComplete` | boolean | True only when exhaustive; cannot be true for an empty list. |
| `asOf` | ISO timestamp string | When the evidence was current. |
| `freeText` | string ≤ 4,000 | Short factual summary or explicit constraints; read as evidence. |

Leave unknown facts empty. The scorer treats an empty field as unknown, never
as a contradiction, so guessing can only lower quality.

## Limits that cannot be raised in the input

- 200 unique jobs per run, 8 concurrent AI calls, 10 concurrent source
  requests.
- Résumé uploads: 5 MB, 50 pages, 8,000 readable characters.
- Job descriptions: 20,000 characters.
- Owner-paid model route: a fixed $0.25 provider circuit breaker per run and
  at most two provider attempts per AI call. When the breaker trips, later
  AI-dependent evaluations become unbilled `ai_failed` rows in audit mode;
  shortlist mode filters those rows out.
- `callOptions.maxTotalChargeUsd` limits how many jobs can be evaluated
  before their scores are known, so a low cap can stop evaluation early.
