# Basic n8n template: LinkedIn jobs to Google Sheets

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

Select it in **Run Actor on Apify**. The workflow sends the token in the
authorization header, never in the URL.

For a dedicated token, keep **Limit token permissions** enabled, grant
account-level **Actors: Run**, allow default run storage access, and use **Full
access** as the running-Actor permission mode because this is the explicitly
trusted Actor. Do not reuse a default account token for client installations.

The HTTP node uses a five-minute timeout and an Apify charge cap. Keep searches
bounded so the synchronous run can finish inside that window.

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
- `actorBuild`, pinned to the live-tested `0.6.19` build;
- `postedWithin`: `1h`, `24h`, `7d`, `30d`, or `any`;
- `workArrangementsCsv`: `remote`, `hybrid`, `onsite`, or a comma-separated
  combination; use an empty string for no workplace filter;
- `maxItems`, initially `1` for the smoke test;
- `maxTotalChargeUsd`, the per-run Apify safety cap.

Translation, AI enrichment, Actor-side cross-run deduplication, analytics, and
raw descriptions are disabled in the starter request.

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
test.

## Security notes

- Never put an Apify token in the workflow URL, Configuration node, Git, or
  screenshots.
- Use a dedicated scoped Apify token and rotate it if exposed.
- Limit spreadsheet sharing to the intended client or team.
- Review LinkedIn's terms and applicable law for the intended use case.

## References

- [n8n workflow import/export](https://docs.n8n.io/workflows/export-import/)
- [n8n Google Sheets append or update](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.googlesheets/sheet-operations/)
- [Apify synchronous Actor dataset endpoint](https://docs.apify.com/api/v2/act-run-sync-get-dataset-items-post)
- [Apify API authentication](https://docs.apify.com/api/v2)
