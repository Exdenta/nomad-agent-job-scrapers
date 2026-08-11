# Basic n8n templates: normalized jobs to Google Sheets

## EURAXESS private `1.0` template

Import
[euraxess-jobs-to-google-sheets.json](euraxess-jobs-to-google-sheets.json) for
the strict EURAXESS `1.0` contract. It starts a bounded search, requires a
complete `nomad-agent-fleet-run-summary-v2`, validates EURAXESS six-root rows,
and appends or updates Google Sheets on `euraxess:<externalId>`.

Before enabling the workflow, use `fetch-actor-details` and confirm the
private deployment exposes `nomad-agent-job-search-input-v1`,
`nomad-agent-job-v1`, and the fleet-v2 run summary. The template defaults to
`maxItems=5`, pins Actor version `1.0`, accepts EURAXESS date windows `24h`,
`7d`, `30d`, or `any`, and never automatically starts another paid run.
Importing the JSON supplies no Apify or Google credential and does not activate
the workflow. Private Actor build `1.0.4` now exposes the target contract under
the `canary` tag, but this asset remains offline-validated only: no EURAXESS
n8n/Google Sheets destination smoke test has completed.

## LinkedIn template

Import [linkedin-jobs-to-google-sheets.json](linkedin-jobs-to-google-sheets.json)
to run a bounded LinkedIn job search, validate and flatten the normalized
records, and append or update rows in Google Sheets.

The template was live-validated on 2026-08-09 with n8n Cloud, Apify Actor
build `0.6.19`, and Google Sheets. No credentials or destination identifiers
from that test are stored in this repository.

## Import the public template

Use n8n's **Import from URL** action with:

```text
https://raw.githubusercontent.com/Exdenta/nomad-agent-job-scrapers/main/integrations/n8n/linkedin-jobs-to-google-sheets.json
```

Alternatively, download the JSON and use **Import from File**. The workflow
imports inactive, starts with a one-result smoke test, and validates required
configuration before starting a paid Actor run.

## Workflow

```text
Schedule or manual run
  -> Configuration
  -> Validate template setup
  -> Run Actor on Apify
  -> Read RUN-SUMMARY
  -> Retry requested?
       yes -> Wait until the recommended time -> retry once
       no  -> Get delivery run jobs
  -> Validate and flatten jobs
  -> Google Sheets append-or-update on jobKey
```

The Actor remains the source of canonical `nomad-agent-job-v1` records. The
Code node creates the table-oriented `nomad-agent-flat-job-v1` projection; it
does not change the Actor output.

## 1. Prepare Google Sheets

Create a spreadsheet, then import
[google-sheets-columns.csv](google-sheets-columns.csv) into a sheet named
`Jobs`. Keep the 32 header names unchanged. The workflow uses **Append or
Update Row** with `jobKey` as the matching column.

Copy the spreadsheet ID from the URL:

```text
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
```

## 2. Import the workflow

Use **Import from URL** with the public URL above, or use **Import from File**
and select `linkedin-jobs-to-google-sheets.json`.

The workflow uses built-in n8n nodes only. Importing it cannot start a run;
the workflow stays inactive until the user publishes it.

## 3. Add the Apify credential

Create an n8n **Header Auth** credential:

| Field | Value |
| --- | --- |
| Name | `Apify API token` |
| Header name | `Authorization` |
| Header value | `Bearer YOUR_APIFY_TOKEN` |

Select the same credential in **Run Actor on Apify**, **Read RUN-SUMMARY**, and
**Get delivery run jobs**. The workflow sends the token in the authorization
header, never in the URL.

For a dedicated token, keep **Limit token permissions** enabled, grant
account-level **Actors: Run**, allow default run storage access, and use **Full
access** as the running-Actor permission mode because this is the explicitly
trusted Actor. Do not reuse a default account token for client installations.

The Actor request waits up to five minutes and uses an Apify charge cap. Keep
searches bounded so the run can finish inside that window.

## 4. Connect Google Sheets

Open **Upsert jobs in Google Sheets**, select or create a Google Sheets OAuth2
credential, and confirm it can edit the destination spreadsheet.

In **Configuration**, replace:

- `REPLACE_WITH_GOOGLE_SPREADSHEET_ID` with the spreadsheet ID;
- `Jobs` only if the sheet tab uses another name.

## 5. Adjust the search

Edit these non-secret fields in **Configuration**:

- `keyword`;
- `location`, or an empty string for no location filter;
- `actorBuild`, initially pinned to `0.6.19` for the live-tested
  normal-delivery path; change it to a later summary-capable build only after
  that build is deployed and smoke-tested;
- `postedWithin`: `1h`, `24h`, `7d`, `30d`, or `any`;
- `workArrangementsCsv`: `remote`, `hybrid`, `onsite`, or a comma-separated
  combination; use an empty string for no workplace filter;
- `maxItems`, initially `1` for the smoke test;
- `maxTotalChargeUsd`, the per-run Apify safety cap;
- `maxRescheduleRetries`, `1` to honor one structured Actor retry request or
  `0` to disable automatic rescheduling.

Translation, AI enrichment, Actor-side cross-run deduplication, analytics, and
raw descriptions are disabled in the starter request.

## Structured blocked-run retry

After a successful Actor run, the workflow reads `RUN-SUMMARY` from that run's
default Apify key-value store. It waits and starts the same request one more
time only when the record has the supported
`nomad-agent-linkedin-run-summary-v1` schema, `blocked: true`, and
`reschedule.recommended: true`. The remaining delay is calculated from the
Actor's `notBefore` value and is capped by its `afterSeconds` value.

The second run can incur the same per-run charge cap. The workflow never
retries merely because the dataset is empty, and it never blindly retries a
`FAILED`, `TIMED-OUT`, or `ABORTED` run. If the second successful run asks for
another retry, the automatic loop stops and that second run becomes the
delivery run. See the [shared retry contract](../../docs/retry-contract.md).

Automatic retry requires an Actor build that actually persists `RUN-SUMMARY`.
The private `0.6.19` canary used for the original delivery smoke test did not
contain that record, so it safely follows the no-retry path. Deploy and
live-smoke a later build containing the summary persistence before describing
this branch as production-verified.

## 6. Test and publish

1. Execute **Run manually**.
2. Confirm the Actor returned at least one record.
3. Confirm the `Jobs` sheet contains one row per `jobKey`.
4. Run it again and verify that the same job updates instead of creating a
   duplicate row.
5. Adjust the search and raise `maxItems` only after the smoke test succeeds.
6. Publish the workflow to enable the daily schedule.

## Duplicate and update behavior

The workflow has two simple duplicate protections:

1. **Validate and flatten jobs** removes duplicate `jobKey` values within one
   Actor response.
2. Google Sheets append-or-update matches on `jobKey`, so recurring runs and
   retries update existing rows instead of appending duplicates.

There is no separate previously-delivered cache. Every run can refresh an
existing Sheet row if the job data changed.

## Live-validation boundary

The reusable JSON was tested end to end on n8n Cloud using a dedicated scoped
Apify Header Auth credential and a Google Sheets OAuth credential. Actor build
`0.6.19` returned one canonical `nomad-agent-job-v1` record; the workflow
validated and flattened it to `nomad-agent-flat-job-v1`, then wrote the row to
Google Sheets with `jobKey` as the matching key. The workflow completed without
an n8n node error. Publishing the schedule was deliberately left out of the
test. The structured `RUN-SUMMARY` retry branch was added later and is covered
by deterministic repository tests; the `0.6.19` canary did not persist the
record required to enter it, and the branch has not yet been forced through a
live LinkedIn block in n8n Cloud.

## Security notes

- Never put an Apify token in the workflow URL, Configuration node, Git, or
  screenshots.
- Use a dedicated scoped Apify token and rotate it if exposed.
- Limit spreadsheet sharing to the intended client or team.
- Review LinkedIn's terms and applicable law for the intended use case.

## References

- [n8n workflow import/export](https://docs.n8n.io/workflows/export-import/)
- [n8n Wait node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/)
- [n8n Google Sheets append or update](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.googlesheets/sheet-operations/)
- [Apify Actor run API](https://docs.apify.com/api/v2/actor-run-get)
- [Apify default key-value store API](https://docs.apify.com/api/v2/default-key-value-store)
- [Apify API authentication](https://docs.apify.com/api/v2)
