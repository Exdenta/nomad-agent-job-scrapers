# LinkedIn Actor retry contract

The LinkedIn Actor writes a structured run summary to its default key-value
store under the key `RUN-SUMMARY`. Integrations must use that record, not a
substring match against the human-readable run status message.

The current record schema is
[`nomad-agent-linkedin-run-summary-v1`](../integrations/shared/linkedin-run-summary-v1.schema.json).
The retry signal is:

```json
{
  "schemaVersion": "nomad-agent-linkedin-run-summary-v1",
  "blocked": true,
  "reschedule": {
    "recommended": true,
    "afterSeconds": 60,
    "notBefore": "2026-08-10T12:01:00Z"
  }
}
```

## Safe behavior

1. Wait until the Actor run is terminal.
2. Continue only when its status is `SUCCEEDED`. Do not blindly retry a
   `FAILED`, `TIMED-OUT`, or `ABORTED` run.
3. Read `RUN-SUMMARY` from that run's default key-value store.
4. Retry only when the record has the exact supported schema,
   `blocked: true`, `reschedule.recommended: true`, and an integer
   `afterSeconds` from 1 through 3600.
5. Prefer `notBefore` when calculating the remaining delay so time already
   spent fetching and validating the record is not waited twice.
6. Start the same Actor input again after the delay. Keep the same per-run
   charge cap and make the possible second paid run visible to the user.
7. Automatically retry at most once. If the second run recommends another
   retry, stop the loop and surface that state for manual handling.
8. Use the retried run as the delivery run. Downstream Sheets/Airtable upserts
   remain idempotent through `jobKey`.

Do not retry merely because a successful dataset is empty. Also do not retry
non-blocking `partial` outcomes such as `deadline`, `upstream-error`, or a
stale-cache fallback without the structured recommendation. A missing summary
means the deployed build does not expose a usable retry instruction; continue
without an automatic retry.

The Actor does not create the second paid run itself. n8n, Make, MCP clients,
or custom API callers must explicitly honor the recommendation.

The basic Make blueprint has a narrower execution-platform bound: it honors
recommendations only through 240 seconds, waits that value exactly, and treats
longer recommendations as no automatic retry. This leaves enough headroom
inside Make's five-minute Free-plan execution limit. Supporting the Actor's
full 3600-second maximum in Make requires a second scheduled scenario and a
persistent handoff, which is intentionally not part of the basic template.

## Deployment boundary

The source contract and integration assets are ahead of the currently tested
private canary. A live `0.6.19` run succeeded and returned jobs, but its default
key-value store contained only `INPUT`, not `RUN-SUMMARY`. Integrations must
therefore treat a missing record as no automatic retry. The Actor must be built
and deployed from source that includes both runtime summary persistence and the
`output.runSummary` link, then smoke-tested, before retry can be claimed as
live-verified.
