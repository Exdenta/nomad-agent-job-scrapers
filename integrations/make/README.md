# Basic Make blueprints: normalized jobs to Google Sheets

## EURAXESS private `1.0` blueprint

Import
[euraxess-jobs-to-google-sheets.blueprint.json](euraxess-jobs-to-google-sheets.blueprint.json)
to process completed runs from a private EURAXESS Apify Task. Replace
`REPLACE_WITH_PRIVATE_EURAXESS_TASK_ID`, connect the Apify and Google Sheets
modules, and keep the Task pinned to Actor version `1.0` with a small item and
charge cap for the first smoke test.

This blueprint requires a complete `nomad-agent-fleet-run-summary-v2`, accepts
only EURAXESS canonical rows, and has no automatic paid-retry route. The
blueprint contains no credential or account connection, imports inactive, and
is offline-validated only; it is not evidence that the private Actor or Make
delivery path has been live-tested.

## LinkedIn blueprint

Import
[linkedin-jobs-to-google-sheets.blueprint.json](linkedin-jobs-to-google-sheets.blueprint.json)
to watch completed LinkedIn Apify Task runs, honor the Actor's structured retry
recommendation once, flatten normalized records, and append or update rows in
Google Sheets.

This is the same deliberately small workflow as the basic n8n pack. It has no
Slack, email, Airtable, data store, or separate delivery cache.

## Workflow

```text
Completed LinkedIn Apify Task run
  -> Apify Task webhook trigger
  -> Configuration
  -> Read RUN-SUMMARY
  -> Retry or deliver
       retry: wait afterSeconds -> run the same Task once
       deliver: get normalized jobs
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

Create an Apify Task for **LinkedIn Jobs Scraper — Normalized Contract** and
save the search input in that Task. Create the webhook in **Watch completed
LinkedIn Task runs** and select this Task. Then select the same Apify connection
in **Get normalized jobs** and **Retry the same Apify Task once**.

Copy the Task ID from Apify and replace `REPLACE_WITH_APIFY_TASK_ID` in
**Configuration**. The trigger and this configuration value must point to the
same Task. Reusing an Apify Task is what makes a retry repeat the exact saved
request without copying Actor input into Make.

Make's Apify connection stores the API token; the blueprint contains no token.
Use a dedicated scoped token that can receive the Actor completion webhook and
read its run dataset.

The **Read structured RUN-SUMMARY** HTTP module needs no separate credential:
the Task webhook supplies the run's signed `output.runSummary` URL. Keep
**Evaluate all states as errors** disabled so an older run with no summary
record can continue to normal delivery without being retried.

This completion-trigger design is intentional. Make's synchronous **Run an
Actor** action waits at most 120 seconds, which is too short for this Actor's
production deadline reserves. Run or schedule the Task in Apify; Make starts
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

In **Configuration**, set `apifytaskid` and keep `maxitems=1` for the first Make
smoke test. This
limits how many completed-run dataset items Make imports; it does not change
the Actor's own input.

Configure the actual search, build, item limit, and spending cap in the Apify
Task. For
the first test, use a build whose published input/output contract matches these
pre-release `0.6` assets, `maxItems=1`, and a conservative run charge cap. Do
not assume `0.6` is Store-published merely because a private canary build
exists. The public blueprint intentionally contains no Actor input or billing
configuration.

## 6. Test and schedule

1. Click **Run once** so Make starts listening for the webhook.
2. Run the configured LinkedIn Task in Apify and confirm it returned at least one
   canonical job.
3. Confirm the `Jobs` sheet contains one flat row per `jobKey`.
4. Run the same Actor input again. The same `jobKey` must update its row rather than
   append a duplicate.
5. Increase `maxItems` only after the one-job smoke test succeeds.
6. Activate the Make scenario, then schedule the Task in Apify, for example
   once per day.

Make stores activation and Apify stores the Actor schedule separately from the
exported blueprint. An imported copy is not activated automatically.

Use an Apify-native Task schedule or start the first run manually in Apify if
you want automatic retry. Runs originally started through an arbitrary API
client are conservatively delivered without an automatic retry, because Make
uses `meta.origin=API` to recognize the one retry it started and prevent a
retry loop.

## Retry behavior

The workflow never parses a human status message. It retries only when a
successful run exposes a valid `RUN-SUMMARY` with all of these values:

- `schemaVersion=nomad-agent-linkedin-run-summary-v1`;
- `blocked=true`;
- `reschedule.recommended=true`;
- integer `reschedule.afterSeconds` from 1 through 240 for this basic Make
  template;
- a present `reschedule.notBefore` value;
- the completed run was not itself started by Make's API retry.

Make waits the full `afterSeconds` value and starts the same Task
asynchronously. Make caps one Sleep at 300 seconds and the Free plan caps the
whole scenario at five minutes, so this simple one-scenario asset uses a
240-second ceiling to leave time for the surrounding modules. Longer Actor
recommendations are delivered without an automatic retry. Supporting the full
Actor maximum of 3600 seconds in Make requires Make's documented multi-scenario
pattern and persistent handoff state, which is intentionally outside this
basic template. The retried run is delivered even if it asks again, so this
workflow can create at most one additional paid Actor run.

Failed, timed-out, aborted, empty-success, deadline-partial, and ordinary
upstream-partial runs are not retried. A missing, older, malformed, or
longer-than-240-second recommendation also never triggers another run. Existing
dataset rows can still be delivered when the summary is absent; an
exact-schema summary with an invalid or unsupported retry request fails closed
to delivery rather than creating a loop.

Automatic retry requires an Actor build that actually writes `RUN-SUMMARY` to
the run's default key-value store. The private `0.6.19` canary advertised the
signed output link but did not persist that record, so it can follow only the
normal-delivery branch. Deploy and live-smoke a later build containing the
summary persistence before treating the retry branch as production-verified.

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

The blueprint JSON, asynchronous Task handoff, strict bounded retry route,
native 32-column projection, credential hygiene, and router structure are
covered by offline repository tests. On 2026-08-09, the Make completion
webhook, dataset retrieval, append
route, and duplicate-update route were historically live-validated against a
private `0.6` canary build and Google Sheets. This is integration evidence, not
Store-publication or general production-readiness evidence. The public
blueprint was corrected from the observed
webhook payload and remains credential-free. The new retry branch has not yet
been live-block-tested because the available `0.6.19` run lacked its
`RUN-SUMMARY` record. A synchronous test also proved
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
- [Make Tools and Sleep limits](https://help.make.com/tools)
- [Make plan execution limits](https://www.make.com/en/pricing)
