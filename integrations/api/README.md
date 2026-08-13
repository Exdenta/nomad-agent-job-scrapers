# REST API and webhook integration

The Apify REST API transports the complete Actor input without an
integration-specific subset. Pin the exact qualified build in the run query:

| Actor | API Actor identifier | Required build |
| --- | --- | --- |
| LinkedIn | `nomad-agent~linkedin-enrich-translate-normalize-scraper` | `0.6.38` |
| EURAXESS | `nomad-agent~euraxess-enrich-translate-normalize-scraper` | `1.0.8` |

EURAXESS is private, so the caller must have account access. Keep the exact
build query even when `latest` currently points to the same build.

## Start one bounded run

Use the JSON file for the selected Actor as the request body. Keep credentials
in the `Authorization` header, never in the URL or input:

```bash
curl --request POST \
  --header "Authorization: Bearer $APIFY_TOKEN" \
  --header "Content-Type: application/json" \
  --data @integrations/api/linkedin-search.json \
  "https://api.apify.com/v2/acts/nomad-agent~linkedin-enrich-translate-normalize-scraper/runs?build=0.6.38&maxTotalChargeUsd=0.10"
```

For EURAXESS, substitute its Actor identifier, body file, and
`build=1.0.8`. The examples request at most five items and disable paid,
stateful, raw, and analytics options. A caller may pass every field in the
current input schema; see the
[compatibility matrix](../../docs/integration-compatibility.md).

The start response identifies a run. Poll that exact run until its terminal run status is available:

1. continue only for `SUCCEEDED` and exit code `0` when present;
2. require the response's `buildNumber` to equal the requested build;
3. read `RUN-SUMMARY` from the same run's default key-value store and validate
   `nomad-agent-fleet-run-summary-v2`;
4. continue only when the factual root and selected-source status are
   `succeeded` or `empty`;
5. fetch and paginate the same run's default dataset and require its total row
   count to equal `RUN-SUMMARY.delivered`;
6. require every item to have exactly `schemaVersion`, `identity`, `data`,
   `custom`, `llm`, and `raw` at its root.

Both API profiles use the factual status before the dataset and start no automatic paid retry.
A valid `empty` status plus zero dataset rows means no
matching jobs. Failed, aborted, timed-out, wrong-build, missing/invalid summary,
degraded summary, count mismatch, or malformed output stops delivery.
`errors[].retryable` is diagnostic and never authorizes a new run.

## Webhooks

Use an Apify Actor/Task run webhook when the consumer should start only after
completion. Treat the webhook as a signal containing a run identity, not as a
trusted replacement for the run or dataset:

1. verify the request according to the receiver's authentication design;
2. retrieve the referenced run from Apify;
3. require the exact Actor, build, and terminal status;
4. read storage IDs only from that run;
5. process each run ID idempotently;
6. apply the same terminal-status, factual `RUN-SUMMARY`, and dataset rules as
   the polling flow.

For Make, use the maintained Task-completion blueprint instead of rebuilding
this receiver. Its Task must carry the same exact build and bounded input.

## Feature and security boundary

- The request body is the Actor input, so `linkedinSearch`,
  `strictGeography`, `companyProfileEnrichment`, `companyFilters`, `filters`,
  `euraxessSearch`, enrichment, translation, raw output, dedupe, analytics,
  and every shared field remain available where supported by that Actor.
- Build and charge-cap query parameters are run controls, not Actor input.
- Never log or persist the Authorization header. Use a dedicated scoped token.
- Do not accept a webhook's dataset URL or run status without re-reading the
  referenced Apify run.
- These recipes are credential-free and offline-tested. They do not prove a
  caller's private EURAXESS access or a live webhook destination.

Primary references: [start Actor run](https://docs.apify.com/api/v2/actors-runs-post),
[get Actor run](https://docs.apify.com/api/v2/actor-run-get), and
[Apify webhooks](https://docs.apify.com/platform/integrations/webhooks).
