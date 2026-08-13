# n8n template listing

Copy-ready metadata for GitHub, client handoffs, and a later n8n Creator Hub
submission. Publishing to n8n's template library is a separate reviewed action.

## Title

Find and save new LinkedIn jobs to Google Sheets with Apify

## Short description

Run a scheduled LinkedIn job search with a normalized Apify Actor, validate and
flatten the results, and append or update jobs in Google Sheets without
duplicate rows.

## Who this is for

- Job seekers maintaining a searchable job tracker.
- Recruiters or sourcing teams collecting normalized LinkedIn vacancies.
- Agencies installing a bounded job-search workflow for clients.
- Developers who want stable flat rows in Google Sheets.

## What this workflow does

1. Runs manually or every day at 08:00 UTC.
2. Validates the client-editable configuration before a paid Actor call.
3. Calls `nomad-agent/linkedin-enrich-translate-normalize-scraper` through the
   Apify API using a Header Auth credential.
4. Polls only the original run ID, requires terminal `SUCCEEDED`, exit code 0,
   and the exact configured build, then reads that run's default dataset.
5. Validates canonical `nomad-agent-job-v1` records and projects them to
   `nomad-agent-flat-job-v1` rows.
6. Removes duplicate `jobKey` values within the Actor response.
7. Appends or updates Google Sheets rows using `jobKey` as the match column.

## Requirements

- An Apify account with access to the LinkedIn Actor.
- A dedicated Apify API token configured as an n8n Header Auth credential.
- A Google account and an editable spreadsheet.
- n8n Cloud or self-hosted n8n.

No community node, messaging account, or AI-provider credential is required.

## Setup

1. Import the workflow from the public raw GitHub URL in
   [README.md](README.md).
2. Import [google-sheets-columns.csv](google-sheets-columns.csv) into a tab
   named `Jobs`.
3. Add the same Apify Header Auth credential to all four Apify HTTP nodes.
4. Add a Google Sheets OAuth credential to **Upsert jobs in Google Sheets**.
5. Replace the spreadsheet placeholder and review **Configuration**.
6. Run the default one-job smoke test manually.
7. Confirm the row in Google Sheets, then increase `maxItems` if desired.
8. Publish only when the test is successful.

## Safe defaults

- The workflow imports inactive.
- The schedule does not run until the workflow is published.
- The workflow pins exact public latest build `0.6.39`.
- `maxItems` starts at `1` and the Apify call has a `$0.10` charge cap.
- The workflow validates minimal v3 `RUN-SUMMARY`, may repeat the exact run
  request once on a valid partial recommendation, and reconciles its
  `delivered` count with the selected dataset. A validated `empty` status is
  valid and writes no rows.
- Translation, AI enrichment, analytics, raw descriptions, and Actor-side
  cross-run deduplication are disabled in the starter input. Every current
  Actor field remains available through `advancedInputJson`.

## Duplicate behavior

Within-run duplicates are removed before Google Sheets. Recurring scheduled
runs use Google Sheets append-or-update on `jobKey`, so existing rows are
refreshed instead of duplicated. The template has no separate delivery cache.

## Validation status

Live-tested on 2026-08-09 with n8n Cloud, Apify build `0.6.19`, and Google
Sheets. One canonical Actor result was flattened and written to the destination
Sheet without an n8n node error. The published schedule was not part of the
live test. This is not a live n8n validation for current Actor build `0.6.39`.
The current workflow requires exact terminal success, minimal v3 status, the
hard one-retry bound, and a reconciled default dataset.

## Support and license

Source, issues, and updates:
<https://github.com/Exdenta/nomad-agent-job-scrapers>

The workflow and repository integration code are MIT-licensed. The hosted
Actor implementation and its usage charges are separate from this repository
license.
