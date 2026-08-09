# Basic Make blueprint: LinkedIn jobs to Google Sheets

Import
[linkedin-jobs-to-google-sheets.blueprint.json](linkedin-jobs-to-google-sheets.blueprint.json)
to run a bounded LinkedIn job search, validate and flatten the normalized
records, and append or update rows in Google Sheets.

This is the same deliberately small workflow as the basic n8n pack. It has no
Slack, email, Airtable, data store, or separate delivery cache.

## Workflow

```text
Scheduled or manual scenario run
  -> Configuration
  -> Run LinkedIn jobs Actor
  -> Get normalized jobs
  -> Validate and flatten each job
  -> Find a Google Sheets row by jobKey
  -> Update the existing row or append a new row
```

The Actor remains the source of canonical `nomad-agent-job-v1` records. Make
Code creates the table-oriented `nomad-agent-flat-job-v1` projection; it does
not change the Actor output.

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

Open both Apify modules and select or create the same Apify connection:

- **Run LinkedIn jobs Actor**;
- **Get normalized jobs**.

Make's Apify connection stores the API token; the blueprint contains no token.
Use a dedicated scoped token that can run the trusted Actor and read its run
dataset.

The blueprint uses Actor ID `kqIdAA2UQiPdOtzEB`, build `0.6.19`, synchronous
execution, 512 MB of memory, `maxItems=1`, and a `$0.10` maximum charge for the
initial smoke test. Make's native **Run an Actor** module can wait at most 120
seconds, so keep the first run small.

## 4. Connect Google Sheets

Open these three modules and select the same Google Sheets connection:

- **Find row by jobKey**;
- **Update existing job**;
- **Append new job**.

In **Configuration**, replace
`REPLACE_WITH_GOOGLE_SPREADSHEET_ID` with the spreadsheet ID. Change `Jobs`
only if the sheet tab has another name.

Open **Find row by jobKey** and confirm **Continue the execution of the route
even if the module returns no results** is enabled. This is what lets a new
`jobKey` reach the Append Row branch.

## 5. Adjust the search

Edit these non-secret values in **Configuration**:

- `keyword`;
- `location`, or an empty string for no location filter;
- `actorBuild`, pinned to the live-tested `0.6.19` build;
- `postedWithin`: `1h`, `24h`, `7d`, `30d`, or `any`;
- `workArrangementsJson`: `[]`, `["remote"]`, `["hybrid"]`,
  `["onsite"]`, or a JSON array containing several values;
- `maxItems`, initially `1`;
- `maxTotalChargeUsd`, the per-run Apify safety cap.

Translation, AI enrichment, raw descriptions, analytics, and Actor-side
cross-run deduplication are disabled in the starter request.

## 6. Test and schedule

1. Click **Run once**.
2. Confirm the Actor returned at least one canonical job.
3. Confirm the `Jobs` sheet contains one flat row per `jobKey`.
4. Run the same search again. The same `jobKey` must update its row rather than
   append a duplicate.
5. Increase `maxItems` only after the one-job smoke test succeeds.
6. Configure the scenario schedule, for example once per day, and activate it.

Make stores scheduling separately from an exported scenario blueprint, so an
imported copy is not activated automatically.

## Duplicate and update behavior

`jobKey` is always `source:externalId`. The Google Sheets search checks column
B for that value. The router then performs exactly one action:

- an existing `jobKey` updates the matched row;
- a missing `jobKey` appends a new row.

There is no separate previously-delivered cache. Sequential scenario
processing is enabled so two bundles cannot race to append the same key.

## Validation boundary

The blueprint JSON, Actor request, Make Code projection, 32-column mapping,
credential hygiene, and router structure are covered by offline repository
tests. The Actor build and the equivalent n8n-to-Google-Sheets path were
live-validated on 2026-08-09. The eight-module blueprint was also imported and
saved as a real Make scenario on that date. End-to-end Make execution is not
claimed yet because the public blueprint intentionally contains no Apify or
Google account connections.

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
