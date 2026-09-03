# AI Job Search & Fit Scorer integration guide

[`nomad-agent/ai-job-fit-scorer`](https://apify.com/nomad-agent/ai-job-fit-scorer)
turns one résumé or structured candidate profile into a ranked developer-job
shortlist. It can search and deduplicate 10 public job sources in one run, or
score supplied `nomad-agent-job-v1` records. Each retained evaluation costs
$0.02 and includes a raw 0–100 fit, a gate-adjusted 0–5 delivery score,
evidence, gaps, source provenance, and stable destination keys.

This repository supports immutable Actor build `0.1.10`
(`XOOtUsksU2uE89H6l`). Do not replace that pin with `latest` in an automated
workflow without re-running the contract and destination checks.

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
export ACTOR_BUILD_NUMBER="0.1.10"
node integrations/api/ai-job-fit-scorer-run-and-fetch.mjs
```

The starter requests at most five retained evaluations and sets a $0.10 total
result-charge cap. For the smallest paid smoke, copy the input and set
`maxItems`, `maxAiItems`, `maxItemsPerSource`, and `aiConcurrency` to `1`; run
with a $0.02 cap in your own caller.

## Exact-run consumption contract

Every integration should preserve this order:

1. start `nomad-agent/ai-job-fit-scorer` with build `0.1.10`, an explicit input,
   item cap, and maximum total charge;
2. retain the returned run ID and poll only that run to a terminal state;
3. require `SUCCEEDED`, exit code `0`, build number `0.1.10`, and immutable
   default dataset and key-value-store IDs;
4. read `RUN-SUMMARY` from that run and require
   `nomad-ai-job-fit-run-summary-v3`, a usable status, scoring v3, the $0.25
   provider guard, at most two provider attempts, and the single $0.02
   `job-fit-result` meter;
5. read the exact run dataset and require its count to equal
   `RUN-SUMMARY.counts.outputRows`;
6. require one run charge per successful retained row, no charge for
   `ai_failed`, and every row to satisfy `nomad-ai-job-fit-v1`;
7. boundedly re-read the same run and storages when completion metadata has not
   settled yet—never switch to a latest-run shortcut;
8. skip `ai_failed` rows and upsert successful evaluations by `matchKey`.

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

Immutable build `0.1.10` passed two bounded canaries and the shipped REST
starter on 2026-09-03:

- supplied-job run `KuuEnCoMfFbFj3z5R`: one scored row and one reconciled
  `job-fit-result` event;
- LinkedIn + remote-board search run `udTJyz3zJWOkKSNUS`: both sources returned
  one normalized posting, the cap retained one scored row, and one event was
  reconciled;
- REST starter run `uqwj8p5qPU74JUyEo`: the repository's Node client itself
  started, polled, settled, and contract-validated one search result.

Those runs prove the Actor path, not hosted MCP, workflow import, scheduling, or
a named destination write. See the evidence manifest before making a stronger
claim.
