# n8n pack: LinkedIn jobs to Google Sheets and Telegram

Import [linkedin-jobs-to-google-sheets-telegram.json](linkedin-jobs-to-google-sheets-telegram.json)
to run a bounded LinkedIn search every day, validate and flatten the normalized
records, suppress previously delivered jobs, upsert rows in Google Sheets, and
optionally send one Telegram digest.

The public template was live-validated on 2026-08-09 with n8n Cloud, Apify
Actor build `0.6.19`, and Google Sheets. The optional Telegram node remains
disabled and has not been part of the live validation. No credentials or
destination identifiers from that test are stored in this repository.

## Import the public template

Use n8n's **Import from URL** action with this public URL:

```text
https://raw.githubusercontent.com/Exdenta/nomad-agent-job-scrapers/main/integrations/n8n/linkedin-jobs-to-google-sheets-telegram.json
```

Alternatively, download the JSON and use **Import from File**. The workflow
imports inactive, uses a one-result smoke test by default, validates required
configuration before starting a paid Actor run, and cannot send Telegram
messages until that node is explicitly configured and enabled.

## What the workflow does

```text
Schedule or manual run
  -> validate client configuration
  -> Apify synchronous Actor run
  -> strict six-root validation
  -> nomad-agent-flat-job-v1 projection
  -> within-run and cross-run duplicate suppression
  -> Google Sheets append-or-update on jobKey
  -> mark delivery only after Sheets succeeds
  -> optional Telegram digest
```

The Actor remains the source of canonical `nomad-agent-job-v1` records. The
Code node creates the table-oriented `nomad-agent-flat-job-v1` projection; it
does not change the Actor output.

## 1. Prepare Google Sheets

Create a spreadsheet, then import
[google-sheets-columns.csv](google-sheets-columns.csv) into a sheet named
`Jobs`. Keep the header names unchanged. The workflow's Google Sheets node
uses **Append or Update Row** with `jobKey` as the matching column.

Copy the spreadsheet ID from the URL:

```text
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
```

## 2. Import the workflow

In n8n, use **Import from URL** with the URL above, or use **Import from File**
and select `linkedin-jobs-to-google-sheets-telegram.json`. The workflow imports
inactive and the Telegram node is disabled, so importing it cannot start a run
or send a message.

The workflow uses current built-in node types only; no community package is
required.

## 3. Add the Apify credential

Create an n8n **Header Auth** credential with:

| Field | Value |
| --- | --- |
| Name | `Apify API token` |
| Header name | `Authorization` |
| Header value | `Bearer YOUR_APIFY_TOKEN` |

Select it in **Run Actor on Apify**. The workflow intentionally sends the
token in an authorization header, not in the URL, and contains no token
placeholder that could be mistaken for a real secret.

For a dedicated token, keep **Limit token permissions** enabled, grant the
account-level **Actors: Run** permission, allow default run storage access, and
use **Full access** as the running-Actor permission mode because this is your
explicitly trusted Actor. This does not make the token an unrestricted account
token. Do not reuse your default Apify token for client installations.

The HTTP node calls Apify's synchronous dataset endpoint with a five-minute
HTTP/Actor timeout. Apify documents that this endpoint returns HTTP 408 when a
run exceeds 300 seconds, so keep the search bounded.

## 4. Connect Google Sheets

Open **Upsert jobs in Google Sheets**, select or create a Google Sheets OAuth2
credential, and confirm that it can edit the target spreadsheet.

In **Configuration**, replace:

- `REPLACE_WITH_GOOGLE_SPREADSHEET_ID` with the spreadsheet ID;
- `Jobs` only if you used another sheet name.

## 5. Adjust the search

Edit the non-secret fields in **Configuration**:

- `keyword` and `location` (leave `location` empty for no location filter);
- `actorBuild`: pinned to the live-tested `0.6.19` build; change it only after
  validating another deployed build;
- `postedWithin`: `1h`, `24h`, `7d`, `30d`, or `any`;
- `workArrangementsCsv`: any comma-separated combination of `remote`,
  `hybrid`, and `onsite`; use an empty string for no workplace filter;
- `maxItems`: the result ceiling; the template starts at `1` for the smoke test
  and can be raised after the first successful run;
- `maxTotalChargeUsd`: the Apify per-run safety cap.

The default run disables translation, AI enrichment, Actor-side cross-run
deduplication, analytics, and raw descriptions. That keeps the starter flow
bounded and avoids copying full descriptions into Google Sheets. Advanced
users can change the JSON body in **Run Actor on Apify** explicitly.

## 6. Test safely

1. Leave **Send Telegram digest** disabled.
2. Execute **Run manually**.
3. Confirm the Actor node returned records and the `Jobs` sheet contains one
   row per `jobKey`.
4. Run it again. Google Sheets should update matching rows rather than append
   duplicates.
5. Adjust the search and raise `maxItems` only after the bounded smoke test.
6. Publish the workflow to enable the schedule.

n8n does not persist workflow static data during manual tests. Once the
workflow is published and invoked by its trigger, it retains up to 5,000 seen
job keys for 90 days. Google Sheets upsert remains the durable duplicate guard
even if that notification cache is empty or reset.

## 7. Enable Telegram (optional)

Create a Telegram Bot credential in n8n and add the bot to the target chat or
channel. Put the chat ID or `@channelusername` in `telegramChatId`, select the
credential on **Send Telegram digest**, then enable the node. The workflow
sends one HTML-formatted digest, capped below Telegram's message-size limit,
instead of one message per job.

For email instead, replace the disabled Telegram node with Gmail, SMTP, or
your preferred email node. Map these fields from **Build notification digest**:

| Email field | n8n expression |
| --- | --- |
| Subject | `{{ $json.emailSubject }}` |
| Body | `{{ $json.emailText }}` |

## Duplicate and failure behavior

The workflow has three duplicate barriers:

1. the flattening node removes duplicate `jobKey` values within one Actor
   response;
2. published workflow static data suppresses recently delivered keys before
   destination writes and notifications;
3. Google Sheets append-or-update matches on `jobKey`, so retries do not append
   duplicate rows.

Seen state is written only after the Google Sheets node succeeds. If the Actor,
validation, or Sheets step fails, n8n stops and does not mark those jobs as
delivered. A retry can safely upsert the same keys. If Telegram fails after a
successful Sheets write, the rows remain stored and the next scheduled run
does not resend them automatically.

## Live-validation boundary

The reusable JSON was tested end to end on n8n Cloud using a dedicated scoped
Apify Header Auth credential and a Google Sheets OAuth credential. Actor build
`0.6.19` returned one canonical `nomad-agent-job-v1` record; the workflow
validated and flattened it to `nomad-agent-flat-job-v1`, then wrote the row to
Google Sheets with `jobKey` as the matching key. The workflow completed without
an n8n node error. Schedule publishing and Telegram delivery were deliberately
left out of that test.

## Security notes

- Never put an Apify token in the workflow URL, the Configuration node, Git,
  or screenshots.
- Use a scoped Apify token and rotate it if it is exposed.
- Google Sheets is a collaboration surface. Limit spreadsheet sharing and
  enable `includeRaw` only if everyone with access is allowed to read full job
  descriptions.
- Review LinkedIn's terms and applicable law for your use case.

## Current references

- [n8n workflow import/export](https://docs.n8n.io/workflows/export-import/)
- [n8n Google Sheets append or update](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.googlesheets/sheet-operations/)
- [n8n Telegram node](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.telegram/)
- [Apify synchronous Actor dataset endpoint](https://docs.apify.com/api/v2/act-run-sync-get-dataset-items-post)
- [Apify API authentication](https://docs.apify.com/api/v2)
