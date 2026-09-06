---
name: ai-job-fit-scorer
description: Search developer jobs and score them for one candidate with the Apify Actor nomad-agent/ai-job-fit-scorer. Use to build a bounded search-and-score or score-supplied-jobs input, run it on the exact build through Apify MCP, validate nomad-ai-job-fit-v1 rows and the nomad-ai-job-fit-run-summary-v4 record, and present a shortlist with fit scores, delivery scores, evidence, and gaps.
---

# AI job search and fit scoring

Use this skill for the `nomad-agent/ai-job-fit-scorer` contract. This skill
supports exact build `0.1.22`. Verify Actor availability and the completed
run's build before accepting results.

The Actor takes one candidate (a structured profile, a résumé upload, or
résumé text) and either searches up to 10 public developer-job sources or
scores jobs you supply. Every returned row carries a raw 0–100 `fitScore`,
a gate-adjusted 0–5 `deliveryScore`, a recommendation, blocking gates,
evidence, gaps, and stable keys. Each returned shortlist row costs $0.02. In audit mode, retained
non-failure rows cost $0.02; `ai_failed` rows are never charged. No model key is needed.

The skill and the MCP connection are separate. Installing this skill does not
configure Apify, authorize an account, or store a token. If Apify tools are
unavailable, read [references/client-setup.md](references/client-setup.md).
Prefer hosted Streamable HTTP with OAuth. Never ask for a token in chat or
write one to a repository.

## Compatibility gate before every run

1. Fetch the deployed Actor details to confirm account access and current
   pricing. Local skill text is not evidence of the live price.
2. Use generic `call-actor` with `callOptions.build: "0.1.22"`. Require the
   completed run to report `buildNumber: "0.1.22"` before reading its output.
3. Send exactly one candidate source: `candidateProfile`, `resume`, or
   `resumeText`. Sending two is rejected before any paid work.
4. In `search` mode, `search.keywords` is required. The Actor never invents a
   query from a résumé.
5. Ask only for material missing choices: target roles or keywords, city or
   country for the search, remote or on-site acceptance, and how many results.
6. Start at `maxItems: 5`, set `callOptions.maxItems: 5`, and set
   `callOptions.maxTotalChargeUsd: 0.1`. Raise limits only on request.

## Build a bounded input

Search and score in one run:

```json
{
  "mode": "search",
  "search": {
    "sources": ["linkedin", "remote_boards", "justjoinit"],
    "keywords": ["platform engineer", "backend engineer"],
    "location": "Madrid",
    "postedWithinDays": 7,
    "maxItemsPerSource": 3
  },
  "candidateProfile": {
    "primaryRole": "Platform Engineer",
    "targetTerms": ["Platform Engineer", "Backend Engineer"],
    "skills": ["Python", "PostgreSQL", "Docker"],
    "seniorityLevels": ["mid"],
    "remoteLocations": ["Spain", "European Union"],
    "hybridLocations": ["Madrid, Spain"],
    "onsiteLocations": [],
    "workArrangementPreferencesComplete": true
  },
  "maxItems": 5,
  "resultMode": "shortlist",
  "minDeliveryScore": 2,
  "aiConcurrency": 2
}
```

Apply these rules:

- `search.sources` accepts only these keys: `linkedin`, `remote_boards`,
  `builtin`, `justjoinit`, `nofluffjobs`, `hackernews`, `ycombinator_was`,
  `wttj`, `infojobs`, `tecnoempleo`. Any other key fails the run.
- Only the `search` object narrows what is fetched. Put the city or country in
  `search.location`, ISO codes for Welcome to the Jungle in
  `search.countryCodes`, and remote-only work in `search.remoteOnly`. A
  location in `preferences` or the profile affects scoring only.
- `search.remoteOnly: true` keeps only jobs explicitly marked fully remote and
  drops unknown arrangements, which removes most LinkedIn rows. Do not set it
  by default.
- Fill the profile only with facts the candidate stated. Leave unknown fields
  empty; the scorer treats empty as unknown, never as a contradiction.
- `acceptedWorkArrangements` is optional. When set it must equal exactly the
  arrangements whose location lists are non-empty (`remote`, `hybrid`,
  `onsite`), or the run fails. Prefer leaving it out and filling the lists.
- `seniorityLevels` uses `intern`, `entry`, `junior`, `associate`, `mid`,
  `senior`, `lead`, `staff`, or `principal`.
- `resultMode: "shortlist"` (default) returns only scored rows whose
  `deliveryScore` is at least `minDeliveryScore` (default 2). Use `audit` only
  when the user needs drops, holds, and failures; retained non-failure rows are
  billable, while `ai_failed` rows are not.

To score jobs the user already has, set `mode: "score-jobs"` and exactly one of
`jobs` (inline `nomad-agent-job-v1` records), `sourceDatasetId`, or
`sourceActorRunId`. Read [references/input-contract.md](references/input-contract.md)
before using supplied jobs, résumé inputs, or the advanced scoring knobs.

## Execute through MCP

Only after the compatibility gate passes. Call the MCP tool `call-actor` with
this outer envelope; the bounded input above belongs under `input`:

```json
{
  "actor": "nomad-agent/ai-job-fit-scorer",
  "input": {
    "mode": "search",
    "search": {"sources": ["linkedin"], "keywords": ["platform engineer"], "maxItemsPerSource": 5},
    "candidateProfile": {"primaryRole": "Platform Engineer", "skills": ["Python"]},
    "maxItems": 5, "resultMode": "shortlist", "minDeliveryScore": 2
  },
  "waitSecs": 0,
  "callOptions": {"build": "0.1.22", "maxItems": 5, "maxTotalChargeUsd": 0.1}
}
```

1. Call generic `call-actor`; do not rely on a direct Actor tool or a mutable
   tag such as `latest`.
2. Require the authoritative run to report `buildNumber: "0.1.22"`. If MCP
   omits that field, verify the same run through Apify's authenticated run
   API. A different build is a compatibility failure.
3. Poll non-terminal runs by run ID with `get-actor-run` until terminal.
4. Continue only after `SUCCEEDED` with exit code `0`. Treat `FAILED`,
   `TIMED-OUT`, and `ABORTED` as errors; report the run ID, status message,
   and exit code, and never present a partial dataset as success.
5. Read the same run's default key-value-store record `RUN-SUMMARY` with
   `get-key-value-store-record` and validate it with
   `scripts/validate_run_summary.py`. A summary whose
   `candidate.usedExampleProfile` is `true` scored the built-in example
   candidate, not the user; say so and do not present those rows as the
   user's matches.
6. Fetch the same run's default dataset with `get-dataset-items` and paginate.
7. Validate the rows with `scripts/validate_fit_rows.py`, passing the summary
   so candidate hashes, evaluation time, source provenance, row count, result
   policy, and charge count reconcile. Pass `--run run.json` as well to bind
   the summary to the authoritative run ID, build, and charge receipt.
8. For zero output, inspect the cause: only `cleanEmpty: true` with zero
   evaluations proves a clean empty source. Positive `resultFilteredOut`
   means evaluations were omitted by shortlist policy; report drops, holds,
   and AI failures separately from scores below the threshold. A budget stop
   with no evaluations means the run could not evaluate the available jobs.
   Do not broaden the search or invent a row.
9. If run charges, summary, or dataset counts have not settled, re-read only
   the same run and its storages at most three times over 30 seconds. Stop on
   a remaining mismatch; never start another paid run as a settlement retry.

Read [references/run-summary.md](references/run-summary.md) for the summary
contract and the count arithmetic the validator enforces.

## Validate and present output

```bash
python3 scripts/validate_run_summary.py run-summary.json --expected-build 0.1.22 --run run.json
python3 scripts/validate_fit_rows.py dataset.json --summary run-summary.json --run run.json --table
```

When presenting results:

- order by `deliveryScore`, then `fitScore`, which is the Actor's own order;
- show title, company, location, `deliveryScore`, `fitScore`,
  `recommendation`, `blockingGates`, `why`, `gapSummary`, and the posting URL;
- explain that `deliveryScore` is the number to act on: a high `fitScore`
  with a low `deliveryScore` means a hard requirement was contradicted, and
  `blockingGates` names it;
- never treat an `ai_failed`, `static_hold`, or `forward_cap_hold` row as a
  scored match; in shortlist mode such rows are not returned at all;
- use `matchKey` when storing results per candidate and keep `evaluationKey`
  as the receipt; `jobKey` alone identifies only the posting;
- link to the source posting and keep a human responsible for applying.

Read [references/output-contract.md](references/output-contract.md) for every
row field and the recommendation and status vocabularies.

## Integration boundary

The Actor is stateless: it does not schedule, alert, apply, or learn from
previous runs. Results flow to n8n, Make, Zapier, Google Sheets, or a database
through the repository's integration packs, which upsert by `matchKey`. A
successful Actor run proves the Actor path, not any destination write.
