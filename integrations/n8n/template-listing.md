# n8n template listing copy

Copy-ready metadata for GitHub, client handoffs, and a later n8n template-library
submission. No listing below has been submitted to or published in n8n's
template library. Importing a workflow is artifact availability; it is not
deployment, successful execution, or named-destination proof.

The files import inactive and contain no credentials. A publisher must still
check the current n8n submission fields, import the exact repository artifact,
connect scoped accounts, run the bounded smoke test, inspect the named
destination, and submit through n8n's review flow under separate authority.

## Template 1: LinkedIn jobs to Google Sheets

### Title

Find and save new LinkedIn jobs to Google Sheets with Apify

### Short description

Run a bounded LinkedIn job search, validate normalized results, and append or
update Google Sheets rows by stable job identity without duplicate rows.

### Full description

Turn a repeatable LinkedIn job search into a clean, searchable Google Sheets
tracker. The workflow runs manually or every day at 08:00 UTC, calls the
Job Atlas LinkedIn Actor at build selector `latest`, polls only that run, and
stops unless the terminal status, exit code, build, and factual `RUN-SUMMARY`
are valid.

Successful `nomad-agent-job-v1` records are reconciled with the selected
dataset, flattened to the documented 32-column `nomad-agent-flat-job-v1`
projection, deduplicated within the run, and upserted by
`jobKey = source:externalId`. A valid empty result writes no rows. A usable
partial result can repeat the exact bounded Actor request at most once when the
run summary explicitly recommends it.

The starter keeps translation, AI enrichment, analytics, raw descriptions,
and Actor-side cross-run deduplication off. Advanced users can supply current
Actor fields through `advancedInputJson` without changing the canonical output
contract.

### Apps and services

- n8n Cloud or self-hosted n8n
- Apify through n8n HTTP Request nodes
- Google Sheets
- Built-in Schedule, Manual Trigger, Code, If, Wait, and Set nodes

No community node or AI-provider credential is required.

### Setup

1. Import [`linkedin-jobs-to-google-sheets.json`](linkedin-jobs-to-google-sheets.json).
2. Import [`google-sheets-columns.csv`](google-sheets-columns.csv) into a tab
   named `Jobs`.
3. Create a scoped n8n Header Auth credential with
   `Authorization: Bearer YOUR_APIFY_TOKEN` and assign it to all four Apify
   HTTP nodes.
4. Connect Google Sheets to **Upsert jobs in Google Sheets**.
5. Replace `REPLACE_WITH_GOOGLE_SPREADSHEET_ID` and review
   **Configuration**. Keep build `latest`, `maxItems=1`, and the `$0.10` charge
   cap for the first run.
6. Run the workflow manually and confirm the exact Apify run, dataset count,
   and resulting Sheet row.
7. Publish the schedule only after that smoke test succeeds.

### Verification boundary

Offline tests cover the workflow graph, exact build and charge selectors,
terminal-run checks, minimal v4 status, one-retry bound, canonical validation,
dataset reconciliation, 32-column mapping, and credential hygiene. A
destination-specific live test still requires the publisher's own n8n and
Google Sheets credentials. The template has no separate delivery cache, and
neither the repository artifact nor an Actor canary proves an n8n execution or
named Sheet write.

### Links

- Workflow: [`linkedin-jobs-to-google-sheets.json`](linkedin-jobs-to-google-sheets.json)
- Product guide: <https://nomadagent.dev/actors/linkedin>
- Setup and support: <https://nomadagent.dev/integrations/n8n>
- Actor: <https://apify.com/job-atlas/linkedin-enrich-translate-normalize-scraper>
- Source and issues: <https://github.com/Exdenta/nomad-agent-job-scrapers>

## Template 2: LinkedIn daily job alerts

### Title

Send new LinkedIn jobs to Slack, Telegram, or email with Apify

### Short description

Search daily for fresh LinkedIn jobs, suppress previously delivered matches,
and send each new job to one selected Slack, Telegram, or email destination.

### Full description

Create one bounded daily LinkedIn job alert without maintaining a separate
delivery database in n8n. The workflow runs manually or at 08:00 UTC, validates
its configuration before the paid call, and calls Actor build selector `latest`
through same-run polling and validated dataset retrieval. The starter requests at most ten
jobs and caps the run at `$0.10`.

The Actor's opaque alert scope enables source-side cross-run deduplication, so
later runs return only jobs not previously delivered for that scope. The
workflow then requires strict six-root `nomad-agent-job-v1` rows, derives
`jobKey = source:externalId`, removes within-run duplicates, and routes each
new job to exactly one configured channel. An empty response sends nothing.

This compact alert starter intentionally does not read v4 `RUN-SUMMARY` or
apply its retry advice. Use the Google Sheets tracker when factual run-summary
and dataset reconciliation are required before delivery.

### Apps and services

- n8n Cloud or self-hosted n8n
- Apify through an n8n HTTP Request node
- One destination: Slack, Telegram, or SMTP email
- Built-in Schedule, Manual Trigger, Code, If, and Set nodes

### Setup

1. Import [`linkedin-daily-job-alerts.json`](linkedin-daily-job-alerts.json).
2. Assign a scoped Apify Header Auth credential to **Find only new jobs**, **Poll same alert run**, and **Get verified alert jobs**.
3. In **Alert configuration**, keep build `latest`, choose `slack`,
   `telegram`, or `email`, replace the destination placeholder, and replace
   the alert-scope placeholder with a stable opaque value.
4. Add credentials only to the selected delivery node. Email also needs a
   verified sender address.
5. Keep the ten-item and `$0.10` limits for the first manual run.
6. Confirm the exact Actor response and named destination message before
   publishing the schedule.

### Verification boundary

Offline tests cover the import graph, exact build and cost selectors,
configuration checks, strict canonical-row validation, within-run `jobKey`
deduplication, and single-channel routing. They do not prove a hosted n8n run,
cross-run behavior in a live Actor account, or a Slack, Telegram, or SMTP
delivery. This workflow has not been submitted to Creator Hub or published as
an n8n template.

### Links

- Workflow: [`linkedin-daily-job-alerts.json`](linkedin-daily-job-alerts.json)
- Product guide: <https://nomadagent.dev/actors/linkedin>
- Setup and support: <https://nomadagent.dev/integrations/n8n>
- Actor: <https://apify.com/job-atlas/linkedin-enrich-translate-normalize-scraper>
- Source and issues: <https://github.com/Exdenta/nomad-agent-job-scrapers>

## Template 3: EURAXESS jobs to Google Sheets

### Title

Find and save EURAXESS research jobs to Google Sheets with Apify

### Short description

Collect normalized EURAXESS research and academic jobs, validate the exact
Actor run, and upsert duplicate-safe Google Sheets rows by stable job identity.

### Full description

Build a repeatable tracker for PhD, postdoc, fellowship, research, and faculty
vacancies from EURAXESS. The workflow runs manually or daily, calls the Nomad
Agent EURAXESS Actor at build selector `latest`, polls the original run ID, and
requires terminal success, exit code 0, the expected build, and a valid factual
`nomad-agent-run-summary-v4` record.

The workflow reconciles `RUN-SUMMARY.delivered` with the selected run's
dataset, validates EURAXESS `nomad-agent-job-v1` records, creates the shared
32-column table projection, and upserts Google Sheets by
`jobKey = source:externalId`. A clean empty run writes nothing. A usable
partial run can repeat the same bounded request once only when v4 recommends
it.

The five-result starter leaves optional translation, AI enrichment, analytics,
raw output, and cross-run deduplication off. EURAXESS supports
`postedWithin=24h`, `7d`, `30d`, or `any`; it does not support `1h` because the
source establishes calendar dates rather than posting hours.

### Apps and services

- n8n Cloud or self-hosted n8n
- Apify through n8n HTTP Request nodes
- Google Sheets
- Built-in Schedule, Manual Trigger, Code, If, Wait, and Set nodes

No community node or AI-provider credential is required.

### Setup

1. Import [`euraxess-jobs-to-google-sheets.json`](euraxess-jobs-to-google-sheets.json).
2. Import [`google-sheets-columns.csv`](google-sheets-columns.csv) into a tab
   named `Jobs`.
3. Assign one scoped Apify Header Auth credential to all four Apify HTTP nodes.
4. Connect Google Sheets to **Upsert jobs in Google Sheets**.
5. Replace the spreadsheet placeholder and keep build `latest`, five results,
   and the starter charge cap for the first run.
6. Set a bounded keyword, location, or `euraxessSearch` plan; use
   `advancedInputJson` for other current Actor fields.
7. Run manually, reconcile the Apify dataset with the named Sheet, and publish
   the schedule only after the smoke succeeds.

### Verification boundary

Offline tests cover the workflow graph, exact build selector, bounded polling,
v4 validation, one-retry limit, EURAXESS source checks, dataset reconciliation,
flat projection, and credential hygiene. They do not establish hosted n8n
execution or a named Google Sheets write. Importing the JSON and a separately
successful Actor run remain supporting artifact evidence only.

### Links

- Workflow: [`euraxess-jobs-to-google-sheets.json`](euraxess-jobs-to-google-sheets.json)
- Product guide: <https://nomadagent.dev/actors/euraxess>
- Setup and support: <https://nomadagent.dev/integrations/n8n>
- Actor: <https://apify.com/job-atlas/euraxess-enrich-translate-normalize-scraper>
- Source and issues: <https://github.com/Exdenta/nomad-agent-job-scrapers>

## Template 4: AI job-fit scores to Google Sheets

### Title

Search, score, and save AI job matches to Google Sheets with Apify

### Short description

Search developer-job sources, evaluate each job against a candidate profile,
and upsert evidence-gated fit scores to Google Sheets by candidate-specific ID.

### Full description

Turn a bounded developer-job search into a candidate-specific shortlist. On a
manual trigger, the workflow calls the AI Job Search & Fit Scorer at exact
build `latest`, polls the same run until terminal, validates legacy v3 or the
current `nomad-ai-job-fit-run-summary-v4` result policy and billing fields,
and fetches only that run's dataset.

Valid `nomad-ai-job-fit-v1` evaluations are projected to the separate
21-column `nomad-ai-job-fit-destination-v1` table. The workflow skips
`ai_failed` rows, reconciles successful rows with the `$0.02`
`job-fit-result` events, and upserts Google Sheets by candidate-specific
`matchKey`; `jobKey` alone is not a safe identity for fit evaluations.

The starter searches up to five jobs across selected developer-job sources,
uses a structured candidate profile, and caps the Actor run at `$0.10`. The
hosted Actor supplies the scoring model, so the workflow does not require a
customer AI-provider key.

### Apps and services

- n8n Cloud or self-hosted n8n
- Apify through n8n HTTP Request nodes
- Google Sheets
- Built-in Manual Trigger, Code, If, and Set nodes

### Setup

1. Import [`ai-job-fit-scorer-to-google-sheets.json`](ai-job-fit-scorer-to-google-sheets.json).
2. Import
   [`../shared/ai-job-fit-google-sheets-columns.csv`](../shared/ai-job-fit-google-sheets-columns.csv)
   into a tab named `Job Fit`.
3. Assign a scoped Apify Header Auth credential to every HTTP node and connect
   Google Sheets to **Upsert Google Sheets by matchKey**.
4. Replace the spreadsheet placeholder and edit the structured search and
   candidate profile in **Configuration**.
5. Keep production selector `latest`, five evaluations, and the `$0.10` maximum total
   charge for the first run.
6. Run manually and reconcile the terminal Actor run, v4 summary, charged
   events, exact dataset, and named Sheet rows.
7. Add a schedule only after the complete smoke has succeeded.

### Verification boundary

Offline tests cover the inactive graph, exact build and charge cap,
same-run polling, v3/v4 status and billing validation, v4 shortlist/audit
policy checks, closed fit-row projection, `ai_failed` suppression, 21-column
mapping, `matchKey` upsert, and credential
hygiene. Separately recorded Actor canaries do not prove this n8n workflow or a
named Sheet write. The workflow has not been imported into a hosted n8n account
or submitted to the template library.

### Links

- Workflow: [`ai-job-fit-scorer-to-google-sheets.json`](ai-job-fit-scorer-to-google-sheets.json)
- Product guide: <https://nomadagent.dev/actors/ai-job-fit-scorer>
- Setup and support: <https://nomadagent.dev/integrations/n8n>
- Actor: <https://apify.com/job-atlas/ai-job-fit-scorer>
- Source and issues: <https://github.com/Exdenta/nomad-agent-job-scrapers>

## License

The workflow files and repository integration code are MIT-licensed. Hosted
Actor implementations, Apify usage charges, n8n hosting, and destination-app
charges are separate from the repository license.
