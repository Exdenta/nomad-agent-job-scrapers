# `RUN-SUMMARY` contract: `nomad-ai-job-fit-run-summary-v4`

A completed run writes `RUN-SUMMARY` to its default key-value store. It
contains candidate hashes and counts, never résumé text. A real record is in
[`docs/examples/ai-job-fit-scorer/run-summary.example.json`](https://github.com/Exdenta/nomad-agent-job-scrapers/blob/main/docs/examples/ai-job-fit-scorer/run-summary.example.json);
the JSON Schema is
[`integrations/shared/nomad-ai-job-fit-run-summary-v4.schema.json`](https://github.com/Exdenta/nomad-agent-job-scrapers/blob/main/integrations/shared/nomad-ai-job-fit-run-summary-v4.schema.json).

## Blocks

| Block | What to check |
| --- | --- |
| `schemaVersion` | Must be `nomad-ai-job-fit-run-summary-v4`. |
| `recordType` | `RUN-SUMMARY`. |
| `actor` | `id`, `runId`, `buildId`, `buildNumber`. The build ID and number must equal the authoritative run receipt. |
| `algorithm` | `name: "scoring-v3"` and `interactionStateUsed: false`. |
| `status` | Usable values are `complete`, `partial`, and `empty`. `failed`, `cancelled`, and `aborted` are not usable. |
| `cleanEmpty` | True for a validated empty source; in search mode, inspect each source outcome. |
| `source` | `mode` (`search`, `inline`, `dataset`, `actor-run`), the selected sources, per-source `status`, `querySupport`, `rawFetched`, `normalized`, `afterFilters`, and `errorType`, plus totals and `truncated`. |
| `candidate` | `candidateHash`, `candidateSnapshotHash`, `derivedFromResume`, `resumeChars`, `usedExampleProfile`. |
| `parameters` | `resultMode`, `minDeliveryScore`, `mode`, `maxItems`, `minRankToForward`, `maxAiItems`, `recoverHolds`, `aiConcurrency`. |
| `counts` | See the arithmetic below. |
| `ai` | `provider`, `model`, `profileExtractionUsed`, `providerCostUsd`, `providerCostLimitUsd` (always 0.25), `providerCostReservedUsd`, `providerCostLimited`, `maxProviderAttempts` (always 2), `inputTokens`, `outputTokens`. |
| `billing` | `eventName` (`job-fit-result`), `unitPriceUsd` (0.02), `chargedCount`, `totalChargedUsd`, `budgetAuthorizedCount`, `budgetLimited`. |
| `terminal` | `reason`. |
| `warnings` | Strings. Includes the example-candidate notice when `usedExampleProfile` is true. |

## Count arithmetic

The validator enforces:

```text
staticDropped + staticHeld + aiScored + aiFailed == evaluatedJobs
resultFilteredOut + outputRows == evaluatedJobs
shortlist: billing.chargedCount == outputRows
audit:     resultFilteredOut == 0 and outputRows == evaluatedJobs
           and billing.chargedCount == outputRows - aiFailed
dataset row count == outputRows
```

`sourceJobs` is how many unique jobs entered evaluation; `budgetAuthorizedJobs`
is how many the caller's charge cap allowed; `aiAttempted` equals
`aiScored + aiFailed`.

## Reading an empty dataset

- `evaluatedJobs == 0` and `cleanEmpty == true`: the search verified no
  matching jobs. Report "no jobs found" and do not broaden the search.
- `evaluatedJobs > 0` and `outputRows == 0`: the shortlist policy omitted every evaluation.
  Inspect dropped, held, failed, and scored counts before attributing this to
  the delivery threshold. Offer audit mode
  or a lower `minDeliveryScore` only if the user wants to see them.
- Zero evaluations with `cleanEmpty == false`: inspect the terminal reason
  and budget fields; this does not establish that no jobs were found.
- `status` not usable, or `actor.buildNumber` different from the resolved run receipt: stop and
  report the run ID and status message.

Validate a downloaded record from the installed skill directory:

```bash
python3 scripts/validate_run_summary.py run-summary.json
```

The bundled schemas are checked against the repository copies. The downloaded
example is from build `0.1.22`, run `AkjZ6lVDultxapjdP`, and the built-in
fictional candidate. Its full dataset has three rows; the single-row example
is an excerpt and cannot reconcile against a summary reporting three rows.

Use `--run run.json` to verify the exact authoritative
run receipt. The local validators cannot prove where downloaded files came
from; fetch them by the storage IDs on that same run.
