# Make to Google Sheets

Import either blueprint:

- [`linkedin-jobs-to-google-sheets.blueprint.json`](linkedin-jobs-to-google-sheets.blueprint.json),
  for a Task pinned to LinkedIn build `1.0.2`;
- [`euraxess-jobs-to-google-sheets.blueprint.json`](euraxess-jobs-to-google-sheets.blueprint.json),
  for a Task pinned to EURAXESS build `1.0.16`;
- [`ai-job-fit-scorer-to-google-sheets.blueprint.json`](ai-job-fit-scorer-to-google-sheets.blueprint.json),
  for a Task pinned to AI Job Search & Fit Scorer build `0.1.12`.

The Apify Task owns the complete Actor input, item limit, exact build, and
charge cap. The Make scenario consumes the completed Task run:

```text
completed Task run
  -> require SUCCEEDED and the configured exact build
  -> read minimal RUN-SUMMARY v4 from the completed run store
  -> wait and repeat the same Task at most once when v4 recommends it
  -> fetch the selected run's default dataset
  -> validate source identity and flatten each job
  -> find by jobKey
  -> update the existing row or append a new row
```

The blueprints read `RUN-SUMMARY` through the Actor output schema's signed
`output.runSummary` link. Only a valid usable `partial` v4 outcome can pass the
one bounded sleep-and-retry route; API-origin retried Task runs cannot enter
that route again. A valid `empty` status writes no rows; missing, invalid,
failed, aborted, timed-out, or wrong-build runs do not enter delivery.

The fit-scoring blueprint accepts the distinct legacy v3 or current
`nomad-ai-job-fit-run-summary-v4`/`nomad-ai-job-fit-v1` contract. Its native
routes distinguish v4 `shortlist` and `audit` policies, require the single
`$0.02` event configuration, skip `ai_failed`, and upsert the
21-column fit projection by candidate-specific `matchKey` rather than
source-only `jobKey`.

## Setup

1. Create an Apify Task with the selected Actor, complete strict v1 input,
   exact build, bounded item limit, and conservative charge cap.
2. Import the matching blueprint and select that Task in **Watch completed Task
   runs**.
3. Set `actorbuild` to the same exact build used by the Task.
4. Import [`google-sheets-columns.csv`](google-sheets-columns.csv) into a sheet
   named `Jobs`.
5. Replace the spreadsheet placeholder and select the Google Sheets connection
   on the lookup, update, and append modules.
6. Start with one result for LinkedIn or five for EURAXESS, with optional
   translation, AI enrichment, analytics, raw output, and cross-run dedupe off.
7. Activate the scenario only after a manual Task-to-Sheets smoke succeeds.

For the scorer, import
[`../shared/ai-job-fit-google-sheets-columns.csv`](../shared/ai-job-fit-google-sheets-columns.csv)
into a sheet named `Job Fit`, set the Task's maximum total charge to `$0.10`,
and keep five evaluations for the first run.

Do not put retired fields such as `replayEpoch` in the saved Task input.

## Output and duplicate behavior

The scenario derives the shared 32-column `nomad-agent-flat-job-v1` projection
and upserts by `jobKey = source:externalId`. Array fields are serialized as JSON
text with JSON escaping while preserving `null` versus `[]`. The formula uses
`__NOMAD_JSON_SEP__` as a reserved separator; supported Actor enum/string array
values never contain it. Do not reuse that formula for uncontrolled arrays.
`descriptionText` comes from `raw.description`; it is `null` when raw output is
disabled.

The flat row does not replace the canonical six-root dataset. Preserve the
canonical record when downstream logic needs nested requirements, contacts,
custom fields, raw evidence, or provenance.

## Validation boundary

The blueprint graphs, exact-build and v4 filters, one-retry bound, 32-column
mapping, source checks, and credential hygiene are covered by offline tests. A
destination-specific live test still requires the client's own Make and Google
Sheets credentials. Importing a blueprint supplies no credentials and does not
activate the scenario.
