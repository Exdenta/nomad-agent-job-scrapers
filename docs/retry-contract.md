# Factual run completion and no-automatic-retry policy

LinkedIn and EURAXESS integrations use the same delivery gate:

1. Pin one exact Actor build and a conservative item and charge cap.
2. Poll or wait until the run is terminal.
3. Continue only for `SUCCEEDED` with exit code `0` when the API exposes it.
4. Verify the run used the requested exact build.
5. Read and semantically validate the same run's default key-value-store
   `RUN-SUMMARY` as `nomad-agent-fleet-run-summary-v2`.
6. Continue only for root and selected-source status `succeeded` or `empty`.
7. Fetch that run's default dataset and require its total item count to equal
   `RUN-SUMMARY.delivered`.
8. Validate every row as the six-root `nomad-agent-job-v1` contract and require
   the expected `identity.source`.
9. Treat a valid `empty` summary plus zero dataset rows as “no matching jobs.”

The checked-in integrations never start an automatic second paid run. They use
`RUN-SUMMARY` only as factual delivery evidence, never as retry authority.
`errors[].retryable` means the failed operation might succeed if a caller later
chooses another run; it does not schedule or authorize that run. Human status
messages, empty output, failed runs, timeouts, and partial rows are not retry
signals. A caller may retry only after an explicit user or operator decision.

Missing, invalid, `partial`, `failed`, or `deadline` summaries stop delivery.
This keeps degraded source outcomes distinct from a positively established
empty search even when the outer Apify run itself is `SUCCEEDED`.
