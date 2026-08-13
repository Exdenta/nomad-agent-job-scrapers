# Factual fleet-v2 RUN-SUMMARY

Every non-cancelled Actor run attempts to write `RUN-SUMMARY` in its default
key-value store. The record uses the closed discriminator
`nomad-agent-fleet-run-summary-v2`.

The root and each selected source use one of: `succeeded`, `empty`,
`partial`, `failed`, or `deadline`. Only `succeeded` and `empty` are
eligible for dataset delivery.

- `empty` is a positively established empty source result, not merely zero
  delivered rows.
- `partial` preserves surviving rows plus degradation.
- `failed` and `deadline` preserve terminal failure facts.
- Funnel counts are monotonically non-increasing from `cardsSeen` through
  `delivered`.
- Root `delivered` equals the sum of source delivered counts and must equal
  the complete default dataset row count before delivery.
- Missing or invalid status stops delivery.

`errors[].retryable` is a diagnostic fact about the failed operation. The
summary contains no retry schedule, does not authorize another paid run, and
must never be converted into an automatic retry. Only an explicit caller or
operator decision may start a new run.

Validate a downloaded record from the installed skill directory:

```bash
python3 scripts/validate_run_summary.py run-summary.json
```
