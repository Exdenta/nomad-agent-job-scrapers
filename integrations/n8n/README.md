# n8n to Google Sheets

Import either inactive workflow:

- [`linkedin-jobs-to-google-sheets.json`](linkedin-jobs-to-google-sheets.json),
  pinned to LinkedIn build `0.6.40`;
- [`euraxess-jobs-to-google-sheets.json`](euraxess-jobs-to-google-sheets.json),
  pinned to private EURAXESS build `1.0.9`.

Both workflows follow the same path:

```text
schedule/manual trigger
  -> validate configuration and complete Actor input
  -> run the exact Actor build with a charge cap
  -> poll that same run ID until terminal
  -> require SUCCEEDED, exit code 0, and the exact build
  -> read and validate minimal RUN-SUMMARY v3
  -> wait and repeat the exact paid request at most once when recommended
  -> fetch the selected run's default dataset
  -> reconcile delivered count, validate, and flatten nomad-agent-job-v1
  -> append or update Google Sheets by jobKey
```

They poll each exact run ID and require `nomad-agent-run-summary-v3`. Only a
valid usable `partial` outcome can request one automatic retry; the same input,
build, item cap, and charge cap are reused. Missing, invalid, wrong-build,
failed, or count-mismatched runs stop before Sheets. A validated `empty` status
writes no rows.

## Setup

1. Create a scoped Apify token and an n8n Header Auth credential with
   `Authorization: Bearer YOUR_APIFY_TOKEN`.
2. Assign that credential to all four Apify HTTP nodes.
3. Import [`google-sheets-columns.csv`](google-sheets-columns.csv) into a sheet
   named `Jobs` and select the Google Sheets credential.
4. Replace `REPLACE_WITH_GOOGLE_SPREADSHEET_ID` in **Configuration**.
5. Keep the starter item count, optional AI/translation, analytics, raw output,
   and cross-run dedupe settings for the first manual smoke.
6. Use `advancedInputJson` for source-specific plans and every current Actor
   field not exposed as a simple configuration value. It must be one JSON
   object and must not contain retired fields such as `replayEpoch`.
7. Publish the workflow only after the manual Actor-to-Sheets smoke succeeds.

EURAXESS accepts `postedWithin` values `24h`, `7d`, `30d`, or `any`; it rejects
`1h` because the source establishes calendar dates, not posting hours.

## Output and duplicate behavior

The workflow validates the six canonical roots and derives the shared
32-column `nomad-agent-flat-job-v1` projection. It uses
`jobKey = source:externalId` as the append-or-update key. Keep the canonical
dataset elsewhere if downstream logic needs nested requirements, contacts,
custom fields, provenance, or the distinction between `null` and `[]`.

## Validation boundary

The exported graphs, exact build selectors, terminal run gate, complete input
pass-through, canonical validation, flat projection, and credential hygiene are
covered by offline tests. A historical LinkedIn n8n Cloud/Google Sheets smoke
used Actor build `0.6.19`; it does not validate the current `0.6.40` workflow.
No EURAXESS n8n/Google Sheets destination smoke has completed. Importing these
files supplies no credentials and does not activate a schedule.
