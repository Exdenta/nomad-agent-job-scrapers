# Output contract: `nomad-ai-job-fit-v1`

Every dataset row is a closed object with exactly these 26 keys. A real row is
in [`docs/examples/ai-job-fit-scorer/fit-row.example.json`](https://github.com/Exdenta/nomad-agent-job-scrapers/blob/main/docs/examples/ai-job-fit-scorer/fit-row.example.json).

| Key | Type | Meaning |
| --- | --- | --- |
| `schemaVersion` | `"nomad-ai-job-fit-v1"` | Row contract discriminator. |
| `matchKey` | 64-hex sha256 | Stable key for one candidate plus one job plus the scoring family. Use it as the destination upsert key. |
| `evaluationKey` | 64-hex sha256 | Content-addressed receipt; changes with the exact candidate snapshot, job content, scoring contract, or evaluation time. |
| `jobKey` | `source:externalId` | Identifies the posting only. Never key a per-candidate table on it alone. |
| `candidateHash` | 64-hex sha256 | Hash of the stable candidate facts. |
| `candidateSnapshotHash` | 64-hex sha256 | Hash of the exact candidate snapshot used. |
| `evaluatedAt` | ISO timestamp, number, or null | When the verdict was produced. |
| `source` | string or null | Source key, for example `linkedin`. |
| `externalId` | string or null | Source-side identifier. |
| `url` | string or null | Canonical posting URL. |
| `title` | string or null | Job title. |
| `company` | string or null | Employer name. |
| `location` | string or null | Raw location text from the posting. |
| `postedAt` | string or null | Posting date when known. |
| `fitScore` | integer 0–100 or null | Raw similarity between candidate and posting. Null for holds and AI failures; static drops explicitly carry zero. |
| `deliveryScore` | integer 0–5 or null | Actionability after hard gates. The number to act on. |
| `recommendation` | enum or null | `exceptional`, `strong`, `plausible`, `weak`, `poor`, `incompatible`, `blocked`, `held`, `unavailable`. |
| `evaluationStatus` | enum | `scored`, `static_drop`, `static_hold`, `forward_cap_hold`, `ai_failed`. |
| `why` | string | Short evidence for the match. Empty for unscored rows. |
| `gapSummary` | string | Short evidence against the match, or what is missing. |
| `blockingGates` | array of strings | Names of hard gates that failed. Empty when none did. |
| `scoreAdjustedForGates` | boolean | True when a failed gate lowered `deliveryScore`. |
| `gates` | object | Per-gate verdicts: `coreRole`, `mandatoryRequirements`, `experienceSeniority`, `workModeLocation`, `explicitPreferences`, each with `status`, `postingEvidence`, and `candidateEvidence`. |
| `staticDecision` | object | The deterministic pre-screen result (action, rank, reasons). |
| `scoring` | object | Receipt: `algorithm: "scoring-v3"`, the provider and model that produced the verdict, and `sourceProvenance` (upstream run, build, dataset). |
| `job` | object | The complete normalized `nomad-agent-job-v1` record that was scored. |

## Reading the two scores

- `fitScore` says how well the posting matches the candidate's skills and
  target roles. Read it together with the gate evidence; it is not an eligibility guarantee.
- `deliveryScore` starts from the fit and is clamped down by every failed
  hard gate: work mode, location, language, work authorization, seniority, or
  role family. A row with `fitScore: 85` and `deliveryScore: 1` has a named
  entry in `blockingGates`.
- Rows are ordered by `deliveryScore`, then `fitScore`.

## Statuses in shortlist versus audit mode

In `shortlist` mode every returned row has `evaluationStatus: "scored"` and
`deliveryScore >= minDeliveryScore`; everything else is neither returned nor
charged. In `audit` mode the dataset also contains:

- `static_drop`: a hard contradiction found before AI; not forwarded.
- `static_hold`: uncertain evidence; not forwarded unless `recoverHolds` is
  true.
- `forward_cap_hold`: eligible but beyond `maxAiItems`.
- `ai_failed`: the model call failed; never charged and never a zero score.

Present only `scored` rows as matches. Mention held or dropped rows only when
the user asked for the audit trail.
