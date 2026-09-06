# Public run completion and one-retry policy

LinkedIn and EURAXESS integrations use the same delivery gate:

1. Select `latest` and a conservative item and charge cap.
2. Poll or wait until the run is terminal.
3. Continue only for `SUCCEEDED` with exit code `0` when the API exposes it.
4. Verify the run used the requested exact build.
5. Read and semantically validate the same run's default key-value-store
   `RUN-SUMMARY` as `nomad-agent-run-summary-v4`.
6. For `partial`, honor `retry.recommended` at most once, using the same exact
   Actor input, build, item cap, and charge cap. Never retry `empty` or a failed
   Apify run.
7. Fetch that run's default dataset and require its total item count to equal
   `RUN-SUMMARY.delivered`.
8. Validate every row as the six-root `nomad-agent-job-v1` contract and require
   the expected `identity.source`.
9. Treat a valid `empty` summary plus zero dataset rows as “no matching jobs.”

The retry object is atomic. `recommended: false` requires `afterSeconds: null`.
`recommended: true` is valid only for a usable `partial` outcome and requires
`afterSeconds` from 1 through 3600.
Each maintained integration enforces a hard maximum of one automatic retry.
After that bound, the latest usable partial dataset may be delivered after its
row count is reconciled. Missing or invalid summaries stop delivery.

`resultsLimited: true` means the Actor knowingly stopped before processing all
available candidates because of an item, billing, scan, or execution bound.
`false` means no known result limit; it does not prove that the external source
was exhaustively searched.

The public summary intentionally contains no source names, funnel counters,
blocking reasons, errors, exception text, requests, responses, or raw data.
