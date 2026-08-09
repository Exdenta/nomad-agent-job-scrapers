# n8n template listing

This file contains copy-ready metadata for GitHub, client handoffs, and a later
submission through the n8n Creator Hub. Publishing to n8n's public template
library is a separate reviewed action and is not implied by committing this
repository asset.

## Title

Find and save new LinkedIn jobs to Google Sheets with Apify

## Short description

Run a scheduled LinkedIn job search with a normalized Apify Actor, validate and
flatten the results, deduplicate them, and upsert new jobs into Google Sheets.
Optionally send one Telegram digest.

## Who this is for

- Job seekers maintaining a searchable job tracker.
- Recruiters or sourcing teams collecting normalized LinkedIn vacancies.
- Agencies installing a bounded, reusable job-monitoring workflow for clients.
- Developers who want stable flat rows without giving up the canonical nested
  source record at the Actor boundary.

## What this workflow does

1. Runs manually or every day at 08:00 UTC.
2. Validates the client-editable configuration before a paid Actor call.
3. Calls `nomad-agent/linkedin-enrich-translate-normalize-scraper` through the
   Apify API using a Header Auth credential.
4. Validates canonical `nomad-agent-job-v1` records and projects them to
   `nomad-agent-flat-job-v1` rows.
5. Deduplicates by `jobKey = source:externalId` within the run and across
   published workflow runs.
6. Appends or updates Google Sheets rows using `jobKey` as the match column.
7. Marks a job as delivered only after the Sheet write succeeds.
8. Builds an optional Telegram or email-friendly digest.

## Requirements

- An Apify account with access to the LinkedIn Actor.
- A dedicated Apify API token configured as an n8n Header Auth credential.
- A Google account and an editable spreadsheet.
- n8n Cloud or self-hosted n8n with the built-in HTTP Request, Code, Set,
  Schedule Trigger, Manual Trigger, and Google Sheets nodes.
- A Telegram bot only if Telegram delivery is enabled.

No community node or AI-provider credential is required.

## Setup

1. Import the workflow from the public raw GitHub URL documented in
   [README.md](README.md).
2. Import [google-sheets-columns.csv](google-sheets-columns.csv) into a tab
   named `Jobs`.
3. Add the Apify Header Auth credential to **Run Actor on Apify**.
4. Add a Google Sheets OAuth credential to **Upsert jobs in Google Sheets**.
5. Replace the spreadsheet placeholder and review the search values in
   **Configuration**.
6. Run the default one-job smoke test manually.
7. Confirm the row in Google Sheets, then increase `maxItems` if desired.
8. Publish the workflow only when the test is successful.

## Safe defaults

- The workflow imports inactive.
- The schedule does not run until the workflow is published.
- Actor build `0.6.19` is pinned because that exact build was live-tested.
- `maxItems` starts at `1` and the Apify call has a `$0.10` charge cap.
- Translation, AI enrichment, analytics, raw descriptions, and Actor-side
  cross-run deduplication are disabled.
- Telegram is disabled and has no credential in the exported JSON.

## Customization

- Change `keyword`, `location`, `postedWithin`, and `workArrangementsCsv` in
  **Configuration**.
- Raise `maxItems` only after the smoke test.
- Replace Telegram with Gmail, SMTP, Slack, or another destination by mapping
  the fields emitted by **Build notification digest**.
- Keep `jobKey` as the Google Sheets matching column.

## Validation status

Live-tested on 2026-08-09 with n8n Cloud, Apify build `0.6.19`, and Google
Sheets. One canonical Actor result was flattened and written to the destination
Sheet without an n8n node error. Telegram and the published schedule were not
part of the live test.

## Support and license

Source, issues, and updates:
<https://github.com/Exdenta/nomad-agent-job-scrapers>

The workflow and repository integration code are MIT-licensed. The hosted
Actor implementation and its usage charges are separate from this repository
license.
