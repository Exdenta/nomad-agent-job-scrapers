# n8n template listing

Copy-ready metadata for GitHub, client handoffs, and a later n8n Creator Hub
submission. Publishing to n8n's template library is a separate reviewed action.

## Template 1: duplicate-safe Google Sheets job tracker

### Title

Find and save new LinkedIn jobs to Google Sheets with Apify

### Short description

Run a scheduled LinkedIn job search with a normalized Apify Actor, validate and
flatten the results, and append or update jobs in Google Sheets without
duplicate rows.

### Who this is for

- Job seekers maintaining a searchable job tracker.
- Recruiters or sourcing teams collecting normalized LinkedIn vacancies.
- Agencies installing a bounded job-search workflow for clients.
- Developers who want stable flat rows in Google Sheets.

### What this workflow does

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

### Requirements

- An Apify account with access to the LinkedIn Actor.
- A dedicated Apify API token configured as an n8n Header Auth credential.
- A Google account and an editable spreadsheet.
- n8n Cloud or self-hosted n8n.

No community node, messaging account, or AI-provider credential is required.

### Setup

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

### Safe defaults

- The workflow imports inactive.
- The schedule does not run until the workflow is published.
- The workflow pins exact supported build `1.0.2`.
- `maxItems` starts at `1` and the Apify call has a `$0.10` charge cap.
- The workflow validates minimal v4 `RUN-SUMMARY`, may repeat the exact run
  request once on a valid partial recommendation, and reconciles its
  `delivered` count with the selected dataset. A validated `empty` status is
  valid and writes no rows.
- Translation, AI enrichment, analytics, raw descriptions, and Actor-side
  cross-run deduplication are disabled in the starter input. Every current
  Actor field remains available through `advancedInputJson`.

### Duplicate behavior

Within-run duplicates are removed before Google Sheets. Recurring scheduled
runs use Google Sheets append-or-update on `jobKey`, so existing rows are
refreshed instead of duplicated. The template has no separate delivery cache.

### Validation status

The workflow is offline-tested for exact terminal success, minimal v4 status,
the hard one-retry bound, canonical validation, and dataset reconciliation. A
destination-specific live test requires the client's own n8n and Google Sheets
credentials.

### Support and license

Source, issues, and updates:
<https://github.com/Exdenta/nomad-agent-job-scrapers>

The workflow and repository integration code are MIT-licensed. The hosted
Actor implementation and its usage charges are separate from this repository
license.

## Template 2: daily new-job alerts

### Title

Send new LinkedIn jobs to Slack, Telegram, or email with Apify

### Short description

Run a bounded daily LinkedIn search, suppress jobs already delivered for this
alert, validate stable job identities, and notify one Slack channel, Telegram
chat, or email address only when new jobs arrive.

### Who this is for

- Job seekers who want one daily alert instead of repeatedly checking searches.
- Recruiters monitoring new vacancies for a role, market, or client.
- Automation builders who need a small, editable Slack, Telegram, or email
  starter without community nodes.

### What this workflow does

1. Runs manually or every day at 08:00 UTC.
2. Validates the exact build, bounded search, cost cap, opaque dedupe scope,
   selected delivery channel, and destination placeholder before a paid call.
3. Calls exact Actor build `1.0.2` through Apify's synchronous dataset
   endpoint with a scoped Header Auth credential.
4. Requires strict six-root `nomad-agent-job-v1` rows from LinkedIn and creates
   `jobKey = source:externalId` without inferring missing facts.
5. Routes each new job to exactly one configured Slack, Telegram, or email node.
6. Sends nothing when the Actor returns no new jobs.

### Setup and safe defaults

1. Import [`linkedin-daily-job-alerts.json`](linkedin-daily-job-alerts.json).
2. Add one Apify Header Auth credential to **Find only new jobs**.
3. Choose `slack`, `telegram`, or `email`, set its destination, and replace the
   alert-scope placeholder with a stable opaque value.
4. Add a credential only to the selected delivery node. Email also requires a
   verified sender address.
5. Run manually before publishing the schedule.

The workflow imports inactive, requests at most ten jobs, caps the run at
`$0.10`, and keeps translation, AI enrichment, raw descriptions, and analytics
off. Actor-side cross-run deduplication is always enabled for the configured
alert scope. It contains no credentials.

### Validation boundary

The import graph, exact build/cost selectors, input checks, canonical row
validation, within-run `jobKey` dedupe, and single-channel routing are
offline-tested. The workflow uses the synchronous dataset endpoint and does not
read v4 `RUN-SUMMARY`. A real destination test still requires the client's own
n8n plus Slack, Telegram, or SMTP credentials. This asset has not been
published to Creator Hub and is not evidence of a live destination test.
