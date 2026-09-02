# n8n job alerts and trackers

Import an inactive, outcome-ready workflow:

- [`linkedin-daily-job-alerts.json`](linkedin-daily-job-alerts.json) searches
  every day and sends only newly delivered jobs to one selected Slack channel,
  Telegram chat, or email address. It pins LinkedIn build `1.0.2`, enables a
  stable Actor dedupe scope, and starts with at most ten jobs;
- [`linkedin-jobs-to-google-sheets.json`](linkedin-jobs-to-google-sheets.json)
  creates a duplicate-safe job tracker by appending or updating the shared flat
  row on stable `jobKey`; it pins LinkedIn build `1.0.2`;
- [`euraxess-jobs-to-google-sheets.json`](euraxess-jobs-to-google-sheets.json)
  creates the same tracker shape for EURAXESS build `1.0.16`.

## Duplicate-safe job tracker

Both workflows follow the same path:

```text
schedule/manual trigger
  -> validate configuration and complete Actor input
  -> run the exact Actor build with a charge cap
  -> poll that same run ID until terminal
  -> require SUCCEEDED, exit code 0, and the exact build
  -> read and validate minimal RUN-SUMMARY v4
  -> wait and repeat the exact paid request at most once when recommended
  -> fetch the selected run's default dataset
  -> reconcile delivered count, validate, and flatten nomad-agent-job-v1
  -> append or update Google Sheets by jobKey
```

They poll each exact run ID and require `nomad-agent-run-summary-v4`. Only a
valid usable `partial` outcome can request one automatic retry; the same input,
build, item cap, and charge cap are reused. Missing, invalid, wrong-build,
failed, or count-mismatched runs stop before Sheets. A validated `empty` status
writes no rows.

## Daily new-job alerts

The alert workflow uses the bounded synchronous dataset endpoint for a shorter
first automation. It requires exact build `1.0.2`, a run charge cap, no more
than 25 requested jobs, strict six-root `nomad-agent-job-v1` rows, LinkedIn
source identity, and stable `jobKey = source:externalId` within-run dedupe.
Actor-side cross-run deduplication is always enabled with the configured opaque
alert scope, so a later scheduled run returns only jobs not previously
delivered in that scope. An empty response sends nothing.

Choose one channel in **Alert configuration**, then add credentials only to the
matching Slack, Telegram, or SMTP node. This compact alert template does not
read v4 `RUN-SUMMARY` or apply its retry advice; use the tracker workflow when
completion-summary reconciliation is required before delivery.

## Tracker setup

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

## Tracker output and duplicate behavior

The workflow validates the six canonical roots and derives the shared
32-column `nomad-agent-flat-job-v1` projection. It uses
`jobKey = source:externalId` as the append-or-update key. Keep the canonical
dataset elsewhere if downstream logic needs nested requirements, contacts,
custom fields, provenance, or the distinction between `null` and `[]`.

## Validation boundary

The exported graphs, exact build selectors, canonical validation, flat
projection, alert routing, and credential hygiene are covered by offline tests.
The tracker additionally covers its terminal run gate and v4 reconciliation.
A destination-specific live test still requires the client's own n8n and
Google Sheets, Slack, Telegram, or SMTP credentials. Importing these files
supplies no credentials and does not activate a schedule.
