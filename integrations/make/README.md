# Basic Make blueprint: LinkedIn jobs to Google Sheets

Import
[linkedin-jobs-to-google-sheets.blueprint.json](linkedin-jobs-to-google-sheets.blueprint.json)
to watch completed LinkedIn Actor runs, validate and flatten their normalized
records, and append or update rows in Google Sheets.

This is the same deliberately small workflow as the basic n8n pack. It has no
Slack, email, Airtable, data store, or separate delivery cache.

## Workflow

```text
Completed LinkedIn Actor run
  -> Apify webhook trigger
  -> Configuration
  -> Get normalized jobs
  -> Validate and flatten each job
  -> Find a Google Sheets row by jobKey
  -> Update the existing row or append a new row
```

The Actor remains the source of canonical `nomad-agent-job-v1` records. Make's
built-in **Set multiple variables** module creates the table-oriented
`nomad-agent-flat-job-v1` projection; it does not change the Actor output and
does not require the paid Make Code app.

## 1. Import the blueprint

In Make, create a blank scenario and choose **Import blueprint**. Select
`linkedin-jobs-to-google-sheets.blueprint.json`.

Make blueprints include modules, settings, and mappings, but never usable
account connections. Every user must connect their own Apify and Google
accounts after import.

## 2. Prepare Google Sheets

Create a spreadsheet, then import
[google-sheets-columns.csv](google-sheets-columns.csv) into a sheet named
`Jobs`. Keep the 32 headers and their order unchanged.

Copy the spreadsheet ID from the URL:

```text
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
```

## 3. Connect Apify

Create the webhook in **Watch completed LinkedIn Actor runs** and select
**LinkedIn Jobs Scraper — Normalized Contract**. Then select the same Apify
connection in **Get normalized jobs**.

Make's Apify connection stores the API token; the blueprint contains no token.
Use a dedicated scoped token that can receive the Actor completion webhook and
read its run dataset.

This completion-trigger design is intentional. Make's synchronous **Run an
Actor** action waits at most 120 seconds, which is too short for this Actor's
production deadline reserves. Run or schedule the Actor in Apify; Make starts
immediately after Apify reports that the run finished.

## 4. Connect Google Sheets

Open these three modules and select the same Google Sheets connection:

- **Find row by jobKey**;
- **Update existing job**;
- **Append new job**.

In **Configuration**, replace the `googlespreadsheetid` value
`REPLACE_WITH_GOOGLE_SPREADSHEET_ID` with the spreadsheet ID. Change
`googlesheetname` from `Jobs` only if the sheet tab has another name.

Open **Find row by jobKey** and confirm **Continue the execution of the route
even if the module returns no results** is enabled. This is what lets a new
`jobKey` reach the Append Row branch.

## 5. Configure the Actor run

In **Configuration**, keep `maxitems=1` for the first Make smoke test. This
limits how many completed-run dataset items Make imports; it does not change
the Actor's own input.

Configure the actual search, build, item limit, and spending cap in Apify. For
the first test, use the currently published `0.6` Actor version, `maxItems=1`,
and a conservative run charge cap. The public blueprint intentionally contains
no Actor input or billing configuration.

## 6. Test and schedule

1. Click **Run once** so Make starts listening for the webhook.
2. Run the LinkedIn Actor in Apify and confirm it returned at least one
   canonical job.
3. Confirm the `Jobs` sheet contains one flat row per `jobKey`.
4. Run the same Actor input again. The same `jobKey` must update its row rather than
   append a duplicate.
5. Increase `maxItems` only after the one-job smoke test succeeds.
6. Activate the Make scenario, then schedule the Actor in Apify, for example
   once per day.

Make stores activation and Apify stores the Actor schedule separately from the
exported blueprint. An imported copy is not activated automatically.

## Duplicate and update behavior

`jobKey` is always `source:externalId`. The Google Sheets search checks column
B for that value. The router then performs exactly one action:

- an existing `jobKey` updates the matched row;
- a missing `jobKey` appends a new row.

There is no separate previously-delivered cache. Sequential scenario
processing is enabled so two bundles cannot race to append the same key.
Runs with an empty dataset are stopped before flattening, so they never create
placeholder rows.

## Free-plan compatibility

The flattening step uses only native Make functions (`first`, `get`, `if`,
`length`, `join`, and `add`) in the built-in Tools app. The six array-valued
fields are stored as compact JSON text. `null` becomes an empty cell while an
explicit empty array remains the literal `[]`.

## Validation boundary

The blueprint JSON, asynchronous Actor handoff, native 32-column projection,
credential hygiene, and router structure are covered by offline repository
tests. On 2026-08-09, the Make completion webhook, dataset retrieval, append
route, and duplicate-update route were live-validated against Actor version
`0.6` and Google Sheets. The public blueprint was corrected from the observed
webhook payload and remains credential-free. A synchronous test also proved
that Make's 120-second Actor action cannot safely start every production run;
the asynchronous completion path is the supported design.

## Security notes

- Never place an Apify token in Configuration, a raw HTTP URL, Git, or a
  screenshot.
- Use a dedicated least-privilege Apify token and rotate it if exposed.
- Limit spreadsheet sharing to the intended client or team.
- Review LinkedIn's terms and applicable law for the intended use case.

## References

- [Make scenario blueprints](https://help.make.com/blueprints)
- [Make Apify app](https://apps.make.com/apify)
- [Make Google Sheets app](https://apps.make.com/google-sheets)
- [Make module types](https://help.make.com/types-of-modules)
