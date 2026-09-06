# AI Job Search & Fit Scorer integration guide

[`nomad-agent/ai-job-fit-scorer`](https://apify.com/nomad-agent/ai-job-fit-scorer)
turns one résumé or structured candidate profile into a ranked developer-job
shortlist. It can search and deduplicate 10 public job sources in one run, or
score supplied `nomad-agent-job-v1` records. Default `shortlist` mode returns
only scored rows whose delivery score meets the threshold. Explicit `audit`
mode retains drops, holds, and failures for pipeline analysis. A charged result
costs $0.02 and includes a raw 0–100 fit, a gate-adjusted 0–5 delivery score,
evidence, gaps, source provenance, and stable destination keys.

This repository pins the live-verified Actor build `0.1.22`
(`XQhyxEg3YZ3NMel70`), which is also the Store `latest` as of 2026-09-05. Keep
automated integrations on `0.1.22` until a newer build is separately
contract-tested. Maintained consumers accept legacy
`nomad-ai-job-fit-run-summary-v3` and current v4 during migration.

Real inputs and outputs live in
[`docs/examples/ai-job-fit-scorer/`](examples/ai-job-fit-scorer/): a
three-source search input, an inline supplied-job input, one real scored row,
and one real `RUN-SUMMARY`. An agent skill that wraps this contract is at
[`.agents/skills/ai-job-fit-scorer`](../.agents/skills/ai-job-fit-scorer/SKILL.md).

## Choose a starter

| Channel | Artifact | What it proves locally |
| --- | --- | --- |
| REST | [`ai-job-fit-scorer-run-and-fetch.mjs`](../integrations/api/ai-job-fit-scorer-run-and-fetch.mjs) | Starts one bounded exact build, polls the returned run, reconciles eventually consistent run/storage receipts, and validates every fit row |
| Hosted MCP | [`ai-job-fit-scorer.mcp.json`](../integrations/mcp/examples/ai-job-fit-scorer.mcp.json) | Supplies generic `call-actor` arguments with an exact build, five-row cap, and $0.10 charge cap |
| n8n | [`ai-job-fit-scorer-to-google-sheets.json`](../integrations/n8n/ai-job-fit-scorer-to-google-sheets.json) | Inactive exact-run workflow with summary, row, billing, and `matchKey` upsert gates |
| Make | [`ai-job-fit-scorer-to-google-sheets.blueprint.json`](../integrations/make/ai-job-fit-scorer-to-google-sheets.blueprint.json) | Task-completion blueprint with native filters and separate update/append routes |
| Zapier | [`ai-job-fit-scorer-template-spec.json`](../integrations/zapier/ai-job-fit-scorer-template-spec.json) | Editor recipe with exact mappings and required live checks; it is not an importable Zap |

All artifacts are inactive and credential-free. Importing or validating one is
not proof that the corresponding hosted channel ran or that a Google Sheet was
written. The exact proof boundary is recorded in
[`integrations/evidence/ai-job-fit-scorer.json`](../integrations/evidence/ai-job-fit-scorer.json).

## Small first run

Use the supplied search fixture, then replace its non-sensitive sample profile
and search terms:

```bash
export APIFY_TOKEN="..."
export ACTOR_BUILD_NUMBER="0.1.22"
node integrations/api/ai-job-fit-scorer-run-and-fetch.mjs
```

The starter requests at most five retained evaluations and sets a $0.10 total
result-charge cap. For the smallest paid smoke, copy the input and set
`maxItems`, `maxAiItems`, `maxItemsPerSource`, and `aiConcurrency` to `1`; run
with a $0.02 cap in your own caller.

The fresh Apify Console form separately provides a fake software-engineer
profile and a three-result cap so it can be tried as-is. Those values are UI
`prefill` examples, not silent API defaults: API and integration callers must
still send exactly one candidate source.

## Input formats

In `search` mode, provide `search.keywords` plus one candidate source. In
`score-jobs` mode, provide exactly one of these job sources:

- `jobs`: a JSON array of complete `nomad-agent-job-v1` objects. Each item has
  exactly the top-level fields `schemaVersion`, `identity`, `data`, `custom`,
  `llm`, and `raw`; `identity` contains `source` plus `externalId` or `url`, and
  `raw.description` contains the posting text. See the complete
  [`linkedin-job.json`](../tests/fixtures/linkedin-job.json) record.
- `sourceDatasetId`: the immutable Apify dataset ID, not its name or URL. Every
  row must use the same complete job contract.
- `sourceActorRunId`: the exact terminal successful upstream run ID, not an
  Actor ID or run URL. Add `expectedSourceBuild` to fail closed unless that run
  used the intended immutable build ID or build number.

Choose exactly one candidate source as well: `candidateProfile`, `resume`, or
`resumeText`. A structured profile needs at least one of `primaryRole`,
`targetTerms`, `skills`, or `freeText`; only add seniority, experience,
language, location, and contract constraints that the candidate actually
provided.

## Choose what the dataset returns

- `resultMode: "shortlist"` is the default. It returns and charges only rows
  with `evaluationStatus: "scored"` whose integer `deliveryScore` is at
  least `minDeliveryScore`. The default threshold is `2`.
- `resultMode: "audit"` preserves every evaluated row, including
  `static_drop`, `static_hold`, `forward_cap_hold`, and `ai_failed`.
  Retained non-failure decisions are charged; `ai_failed` rows are not.
- Raw `fitScore` is not the delivery filter. `deliveryScore` incorporates
  hard role, location, seniority, language, and preference gates that can make
  a superficially high raw fit unsafe to deliver.
- `RUN-SUMMARY` v4 always reports `evaluatedJobs`, `staticDropped`,
  `staticHeld`, `aiScored`, `aiFailed`, `resultFilteredOut`, and
  `outputRows`, so a clean empty shortlist is distinguishable from no work.

## Exact-run consumption contract

Every integration should preserve this order:

1. start `nomad-agent/ai-job-fit-scorer` with build `0.1.22`, an explicit input,
   item cap, and maximum total charge;
2. retain the returned run ID and poll only that run to a terminal state;
3. require `SUCCEEDED`, exit code `0`, build number `0.1.22`, and immutable
   default dataset and key-value-store IDs;
4. read `RUN-SUMMARY` from that run and require
   `nomad-ai-job-fit-run-summary-v4`, a usable status, scoring v3, a valid
   result policy and count partition, the $0.25 provider guard, at most two
   provider attempts, and the single $0.02 `job-fit-result` meter;
5. read the exact run dataset and require its count to equal
   `RUN-SUMMARY.counts.outputRows`;
6. in shortlist mode require every row to be scored and meet the declared
   delivery threshold, with `chargedCount == outputRows`; in audit mode require
   `resultFilteredOut == 0` and charge only retained non-failures;
7. boundedly re-read the same run and storages when completion metadata has not
   settled yet—never switch to a latest-run shortcut;
8. skip `ai_failed` rows at destinations and upsert retained evaluations by
   `matchKey`.

`jobKey` identifies one source posting. It is not a safe candidate-specific
destination key: using it alone can let one candidate's evaluation overwrite
another's. `matchKey` includes stable candidate facts and the scoring family;
`evaluationKey` is the more exact content-addressed receipt.

## Destination shape

Use
[`nomad-ai-job-fit-destination-v1.schema.json`](../integrations/shared/nomad-ai-job-fit-destination-v1.schema.json)
and
[`ai-job-fit-google-sheets-columns.csv`](../integrations/shared/ai-job-fit-google-sheets-columns.csv)
for n8n, Make, Zapier, or another table destination. The Python adapter in
[`ai_job_fit_adapter.py`](../integrations/shared/ai_job_fit_adapter.py) validates
the closed Actor row before projecting it and deliberately omits `ai_failed`
evaluations.

Keep the original `nomad-ai-job-fit-v1` dataset when downstream logic needs the
complete normalized job, gate evidence, scoring receipt, or source provenance.
The flat destination row is a convenience view, not a replacement contract.

## Channel notes

### MCP

Use the scoped hosted server:

```text
https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

Call the generic `call-actor` tool with the supplied descriptor. Then inspect
the exact run and its storages using the remaining scoped tools. A direct Actor
API canary does not prove hosted MCP exposure; test the hosted tool separately
before relying on it.

### n8n

Import the workflow, add Apify Header Auth to every Apify HTTP node, add Google
Sheets OAuth2 to the last node, replace the Sheet placeholders, and import the
shared CSV header. Keep the workflow inactive until one manual run creates a
named row and the same fixture updates that row instead of duplicating it.

### Make

Create an Apify Task that owns the complete bounded input, exact build, and
charge cap. Import the blueprint, connect Apify and Google Sheets, replace both
destination placeholders, and execute once on demand. Native filters can check
declared values but are not a full closed-object schema oracle; retain the
repository tests or Python adapter as the stronger contract check.

### Zapier

Zapier has no portable workflow JSON for this recipe. Build it in the editor
from the supplied specification, keep it off during setup, and add exact-run
API/Webhook steps if the Apify action omits build, storage, or summary fields.
Prove create and update behavior before enabling the schedule.

## Product and source caveats

- The Actor evaluates one candidate per run and is stateless. It does not send
  alerts, learn from clicks, apply to jobs, or make hiring decisions.
- Public sources can change, rate-limit, block, or omit fields. Filter support
  differs by source, and strict `remoteOnly` excludes hybrid and unknown jobs.
- Full description evidence is required. A verified zero-row source can be a
  clean empty outcome; unverified empties or all-source failure fail closed.
- Résumés are processed in memory, but the original Actor input/upload remains
  subject to Apify retention controls. Extracted evidence is sent through the
  configured OpenRouter/OpenAI path with provider data collection denied. No
  zero-data-retention claim is made.
- Scores are decision support. Verify the source posting and keep a human
  responsible for application and hiring decisions.

## Current live proof

Build `0.1.22` (`XQhyxEg3YZ3NMel70`) was read back as both `latest` and
its default selector on 2026-09-05. Existing run `AkjZ6lVDultxapjdP`, started
through `latest`, succeeded with exit code 0, three scored rows and three
`job-fit-result` charges ($0.06). All three selected sources succeeded. This
run used the built-in fictional candidate; it does not describe a customer.
The full dataset and summary reconcile locally against that exact run receipt.
No new paid run was started for this documentation work.

Current starters pin `0.1.22`. The following older runs retain their actual
build IDs and demonstrate historical cases, not fresh audit/inline execution
on `0.1.22`.

### Historical behavior checks

Immutable runtime build `0.1.12` passed four bounded v4 behaviors on
2026-09-03:

- default search `fhMYR6bzdbzdNl84y`: LinkedIn, remote boards, and JustJoinIT
  all succeeded; three jobs were AI-scored, two fell below the default
  delivery threshold, and the one delivery-3 row was returned and charged
  exactly once;
- filtered shortlist `wkk8NkZv43JEIcv3m`: one deterministic hold was counted
  and filtered, leaving an empty dataset and zero result charges;
- audit `lIpiLiudBukaaFI7d`: the same held decision was retained, no row was
  filtered, and the one retained non-failure decision was charged once;
- scored inline job `vzhqlbVeXhp5tKs4N`: one AI-scored row returned
  `fitScore: 92`, `deliveryScore: 5`, and one reconciled result charge.

Public documentation build `0.1.13` then passed exact-build zero-charge smoke
`DZdOvX8FxOtgFS6J7`; its runtime container digest is identical to `0.1.12`.
The older `0.1.10` all-source run `CEofFmV6UEb82yi7M` remains historical
evidence that all ten adapters succeeded together, not current-release proof.

Those runs prove the Actor path, not hosted MCP, workflow import, scheduling, or
a named destination write. See the evidence manifest before making a stronger
claim.
