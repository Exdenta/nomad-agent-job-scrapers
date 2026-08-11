# Fleet-v2 RUN-SUMMARY

The clean EURAXESS `1.0` host attempts to write a structured record to its
default key-value store under `RUN-SUMMARY` for every non-cancelled run. This
is an unreleased local contract, not evidence that the private deployed
`0.5.1` Actor writes it.

Schema discriminator: `nomad-agent-fleet-run-summary-v2`.
The adjacent JSON Schema is structural. Validate cross-field semantics with
the dependency-free `scripts/validate_run_summary.py` helper bundled in this
skill; structural schema validation alone is insufficient.

```json
{
  "schemaVersion": "nomad-agent-fleet-run-summary-v2",
  "status": "succeeded",
  "startedAt": "2026-08-10T10:00:00Z",
  "finishedAt": "2026-08-10T10:02:00Z",
  "partial": false,
  "truncated": false,
  "delivered": 2,
  "sources": {
    "euraxess": {
      "status": "succeeded",
      "searchRequests": 3,
      "cardsSeen": 10,
      "detailsCompleted": 8,
      "normalized": 8,
      "afterFilters": 5,
      "deliveryEligible": 2,
      "delivered": 2,
      "stale": false,
      "blocked": false,
      "stopReason": null,
      "errors": []
    }
  }
}
```

The run and source status set is closed: `succeeded`, `empty`, `partial`,
`failed`, or `deadline`.

- `empty` requires a positively classified empty source response. Zero rows
  after blocking or failure are not empty.
- `partial` represents surviving usable records plus degradation, including a
  stale-cache fallback.
- `failed` means the source/run did not produce a usable successful outcome.
- `deadline` preserves a classified deadline instead of laundering it into an
  empty success.
- Counts move monotonically from cards through delivered rows.
- Top-level `delivered` equals the sum of per-source delivered counts, and the
  top-level status/partial flag must agree with the source outcomes.
- Errors contain only bounded `code`, closed `stage`, and `retryable` fields;
  they contain no raw exception, request, response, source text, or secret.
- `stopReason` is a bounded machine code, not a user-facing message.

This schema reports facts. It has no `reschedule`, `afterSeconds`, or
`notBefore` field and does not authorize an automatic second paid run. Treat a
missing record as missing structured evidence, not as a retry instruction.

Offline validation from the installed skill directory:

```bash
python3 scripts/validate_run_summary.py run-summary.json
```
