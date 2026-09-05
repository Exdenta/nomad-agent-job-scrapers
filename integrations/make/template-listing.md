# Make template listing copy

Copy-ready metadata for GitHub, client handoffs, a shared scenario page, or a
later Make public-template review. No listing below has been submitted to or
published in Make's public templates library. Importing a blueprint is artifact
availability; it is not deployment, successful execution, or named-destination
proof.

The blueprints contain mapped modules and placeholder IDs but no account
connections. Import them into a new scenario, configure the user's Apify Task
and Google Sheets connection, leave the scenario off, and run one bounded
manual Task-to-Sheets smoke before activation. Publishing a team template,
sharing a scenario link, and receiving public-library approval are separate
states.

## Template 1: LinkedIn jobs to Google Sheets

### Title

Save LinkedIn jobs to Google Sheets

### Short description

Watch a completed Apify Task, validate exact LinkedIn build `1.0.2`, flatten
normalized jobs, and update or append Google Sheets rows by stable `jobKey`.

### Full description

Turn a bounded LinkedIn job-search Task into a duplicate-safe Google Sheets
tracker. The scenario watches completed Apify Task runs, requires terminal
`SUCCEEDED` from exact build `1.0.2`, reads the factual
`nomad-agent-run-summary-v4` record through that run's signed output link, and
fetches only the selected run's default dataset.

Each canonical `nomad-agent-job-v1` row is projected with Make's built-in Tools
module to the documented 32-column `nomad-agent-flat-job-v1` table. The
scenario finds an existing Sheet row by `jobKey = source:externalId`, then
updates it or appends a new row. A valid empty result writes nothing. A usable
partial result can wait and repeat the same Apify Task at most once when v4
explicitly recommends it.

The Apify Task—not the blueprint—owns the complete Actor input, one-item
starter limit, exact build, and conservative charge cap. Optional translation,
AI enrichment, analytics, raw output, and cross-run deduplication should remain
off for the first smoke.

### Apps and services

- Make
- Apify: Watch completed Task runs, Run a Task, and Fetch dataset items
- HTTP: read the exact run's signed `RUN-SUMMARY` link
- Tools: configuration, bounded wait, and normalized-row projection
- Google Sheets: search, update, and append rows

### Setup

1. Create an Apify Task for
   `nomad-agent/linkedin-enrich-translate-normalize-scraper` with complete
   strict input, exact build `1.0.2`, a one-item first run, and a conservative
   maximum total charge.
2. Import
   [`linkedin-jobs-to-google-sheets.blueprint.json`](linkedin-jobs-to-google-sheets.blueprint.json)
   into a new Make scenario and select that Task in
   **Watch completed LinkedIn Task runs**.
3. Set `actorbuild` to `1.0.2`, replace the Task and spreadsheet placeholders,
   and connect the Apify and Google Sheets modules.
4. Import [`google-sheets-columns.csv`](google-sheets-columns.csv) into a tab
   named `Jobs`.
5. Keep the scenario off, run the Task once, and reconcile the exact Actor run,
   v4 summary, dataset count, and resulting Sheet row.
6. Activate a schedule only after the named destination smoke succeeds.

### Verification boundary

Offline tests cover the blueprint graph, exact-build and v4 filters, one-retry
bound, 32-column mapping, source checks, update/append routes, and credential
hygiene. The blueprint has not been imported into a live Make account or used
to prove a named Google Sheets write. A public share link or separately
successful Actor canary would not prove marketplace approval or this scenario's
destination delivery.

### Links

- Blueprint: [`linkedin-jobs-to-google-sheets.blueprint.json`](linkedin-jobs-to-google-sheets.blueprint.json)
- Product guide: <https://nomadagent.dev/actors/linkedin>
- Setup and support: <https://nomadagent.dev/integrations/make>
- Actor: <https://apify.com/nomad-agent/linkedin-enrich-translate-normalize-scraper>
- Source and issues: <https://github.com/Exdenta/nomad-agent-job-scrapers>

## Template 2: EURAXESS jobs to Google Sheets

### Title

Save EURAXESS jobs to Google Sheets

### Short description

Watch a completed EURAXESS Task at build `1.0.28`, validate its factual run
summary, and upsert normalized research jobs in Google Sheets by `jobKey`.

### Full description

Create a repeatable Google Sheets tracker for PhD, postdoc, fellowship,
research, and faculty vacancies collected from EURAXESS. The scenario watches
completed Apify Task runs, accepts only terminal `SUCCEEDED` from exact build
`1.0.28`, reads `nomad-agent-run-summary-v4` from the run's signed output link,
and fetches that run's default dataset.

Validated EURAXESS `nomad-agent-job-v1` rows are flattened to the shared
32-column destination projection without replacing the canonical records.
Make searches Google Sheets by stable `jobKey = source:externalId`, updates an
existing row, or appends a new one. A valid empty run produces no write. A
usable partial run can repeat the same Task only once when the v4 summary
recommends it.

The Apify Task owns all search fields, the exact build, five-item starter
limit, and charge cap. For the first smoke, keep translation, AI enrichment,
analytics, raw output, and cross-run deduplication off. EURAXESS supports
`postedWithin=24h`, `7d`, `30d`, or `any`, but not `1h`.

### Apps and services

- Make
- Apify: Watch completed Task runs, Run a Task, and Fetch dataset items
- HTTP: read the exact run's signed `RUN-SUMMARY` link
- Tools: configuration, bounded wait, and normalized-row projection
- Google Sheets: search, update, and append rows

### Setup

1. Create an Apify Task for
   `nomad-agent/euraxess-enrich-translate-normalize-scraper` with complete
   strict input, exact build `1.0.28`, no more than five results for the first
   run, and a conservative maximum total charge.
2. Import
   [`euraxess-jobs-to-google-sheets.blueprint.json`](euraxess-jobs-to-google-sheets.blueprint.json)
   into a new Make scenario and select that Task in
   **Watch completed EURAXESS Task runs**.
3. Set `actorbuild` to `1.0.28`, replace the Task and spreadsheet placeholders,
   and connect Apify and Google Sheets.
4. Import [`google-sheets-columns.csv`](google-sheets-columns.csv) into a tab
   named `Jobs`.
5. Leave the scenario off, run a bounded Task, and reconcile the exact run,
   v4 summary, selected dataset, and named Sheet row.
6. Activate only after the Task-to-Sheets smoke succeeds.

### Verification boundary

Offline tests cover the blueprint graph, exact EURAXESS build, v4 status and
retry filters, source identity, 32-column projection, Sheet mapping, and
credential hygiene. They do not prove a Make import, hosted scenario run, or
named Sheet write. This metadata is preparation for a future review, not a
claim that the template is submitted, approved, shared, or public.

### Links

- Blueprint: [`euraxess-jobs-to-google-sheets.blueprint.json`](euraxess-jobs-to-google-sheets.blueprint.json)
- Product guide: <https://nomadagent.dev/actors/euraxess>
- Setup and support: <https://nomadagent.dev/integrations/make>
- Actor: <https://apify.com/nomad-agent/euraxess-enrich-translate-normalize-scraper>
- Source and issues: <https://github.com/Exdenta/nomad-agent-job-scrapers>

## Template 3: AI job-fit scores to Google Sheets

### Title

Save AI job-fit scores to Google Sheets

### Short description

Watch an AI Job Search & Fit Task at build `0.1.11`, validate evidence-gated
evaluations and billing, and upsert Google Sheets rows by unique `matchKey`.

### Full description

Convert a completed AI Job Search & Fit Scorer Task into a candidate-specific
Google Sheets shortlist. The scenario watches the configured Apify Task,
requires the expected Actor and exact build `0.1.11`, reads that run's
`nomad-ai-job-fit-run-summary-v3`, fetches its exact dataset, and validates the
declared scoring and billing fields before delivery.

The scenario skips `ai_failed` rows and projects successful
`nomad-ai-job-fit-v1` evaluations to the separate 21-column
`nomad-ai-job-fit-destination-v1` table. It finds, updates, or appends rows by
candidate-specific `matchKey`; source-only `jobKey` cannot identify a unique
candidate evaluation. Each retained successful evaluation uses the Actor's
single `$0.02` `job-fit-result` event.

The Apify Task owns the complete bounded search or supplied-job input,
candidate profile or résumé, exact build, item count, and charge cap. Start
with no more than five evaluations and a `$0.10` maximum total charge. The
hosted Actor supplies the model, so no customer AI-provider key is required.

### Apps and services

- Make
- Apify: Watch completed Task runs and Fetch dataset items
- HTTP: read the exact run's `RUN-SUMMARY`
- Tools: configuration and the 21-column fit projection
- Google Sheets: search, update, and append rows

### Setup

1. Create an Apify Task for `nomad-agent/ai-job-fit-scorer` with exact build
   `0.1.11`, complete bounded input, at most five evaluations, and a `$0.10`
   maximum total charge.
2. Import
   [`ai-job-fit-scorer-to-google-sheets.blueprint.json`](ai-job-fit-scorer-to-google-sheets.blueprint.json)
   into a new Make scenario and select that Task in
   **Watch completed AI Job Search & Fit Task runs**.
3. Keep `expectedbuild=0.1.11`, replace the spreadsheet placeholder, and
   connect the Apify and Google Sheets modules.
4. Import
   [`../shared/ai-job-fit-google-sheets-columns.csv`](../shared/ai-job-fit-google-sheets-columns.csv)
   into a tab named `Job Fit`.
5. Leave the scenario off, run one bounded Task, and reconcile the exact Actor
   run, v3 summary, charged events, fit rows, and named Sheet rows.
6. Activate only after the complete destination smoke succeeds.

### Verification boundary

Offline tests cover unique modules, exact Actor/build filters, declared v3
status and billing checks, `ai_failed` suppression, 21-column projection,
`matchKey` update/append routes, and credential hygiene. Make's native filters
do not prove a fully closed JSON object; the repository's n8n and Python tests
remain the stronger local contract oracle. Actor canaries already recorded
elsewhere do not prove this Make scenario or its named Google Sheets write.

### Links

- Blueprint: [`ai-job-fit-scorer-to-google-sheets.blueprint.json`](ai-job-fit-scorer-to-google-sheets.blueprint.json)
- Product guide: <https://nomadagent.dev/actors/ai-job-fit-scorer>
- Setup and support: <https://nomadagent.dev/integrations/make>
- Actor: <https://apify.com/nomad-agent/ai-job-fit-scorer>
- Source and issues: <https://github.com/Exdenta/nomad-agent-job-scrapers>

## License

The blueprint files and repository integration code are MIT-licensed. Hosted
Actor implementations, Apify usage charges, Make operations, and Google
services are separate from the repository license.
