# MCP prompt examples

## LinkedIn

```text
Use generic call-actor for
nomad-agent/linkedin-enrich-translate-normalize-scraper at exact build 0.6.38.
Search for at most 5 remote or hybrid TypeScript developer jobs in Spain from
the last 7 days. Disable translation, AI enrichment, analytics, raw output, and
cross-run dedupe. Use a $0.10 charge cap and waitSecs 0.

Poll with get-actor-run until terminal. Continue only after SUCCEEDED, verify
the exact build through the Apify run API if MCP omits buildNumber, then read
RUN-SUMMARY with get-key-value-store-record. Require a valid
nomad-agent-fleet-run-summary-v2 status of succeeded or empty and reconcile its
delivered count with the same run's dataset from get-dataset-items. Validate every row as
nomad-agent-job-v1 with exactly schemaVersion, identity, data, custom, llm, and
raw. Report a valid empty dataset as no matching jobs. Never start an automatic
retry.
```

## EURAXESS

```text
Use generic call-actor for
nomad-agent/euraxess-enrich-translate-normalize-scraper at exact build 1.0.8.
Search for at most 5 postdoctoral machine-learning jobs in Germany. Disable
translation, AI enrichment, analytics, raw output, and cross-run dedupe. Use a
$0.10 charge cap and waitSecs 0.

Poll with get-actor-run until terminal. Continue only after SUCCEEDED, verify
the exact build through the Apify run API if MCP omits buildNumber, then read
RUN-SUMMARY with get-key-value-store-record. Require a valid
nomad-agent-fleet-run-summary-v2 status of succeeded or empty and reconcile its
delivered count with the same run's dataset from get-dataset-items. Require
identity.source=euraxess and validate the full EURAXESS custom extension.
Report a valid empty dataset as no matching jobs. Never start an automatic
retry or silently broaden the search.
```

For `FAILED`, `TIMED-OUT`, or `ABORTED`, report the run ID, status, status
message, and exit code. Do not present partial dataset rows as success.
