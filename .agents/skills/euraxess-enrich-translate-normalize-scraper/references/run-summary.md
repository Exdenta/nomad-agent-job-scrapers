# Minimal public RUN-SUMMARY v3

A completed usable Actor run writes `RUN-SUMMARY` in its default key-value
store with discriminator `nomad-agent-run-summary-v3`.

The closed public record contains only:

- `schemaVersion`
- `status`: `succeeded`, `empty`, or usable `partial`
- `startedAt` and `finishedAt`
- `truncated`
- `delivered`, which must equal the complete selected dataset row count
- atomic `retry`: `recommended`, `afterSeconds`, and `notBefore`

`succeeded` and `partial` require at least one delivered job. `empty`
requires zero delivered jobs, no truncation, and no retry. A recommended retry
is valid only for `partial`, uses a delay from 1 through 3600 seconds, and may
be honored at most once with the exact same input, build, item cap, and charge
cap.

Source names, funnel counters, blocking reasons, errors, exception text,
requests, responses, and raw source data are not public summary fields. Failed,
timed-out, and aborted Apify runs are governed by terminal run metadata and are
never retried from `RUN-SUMMARY`.

Validate a downloaded record from the installed skill directory:

```bash
python3 scripts/validate_run_summary.py run-summary.json
```
