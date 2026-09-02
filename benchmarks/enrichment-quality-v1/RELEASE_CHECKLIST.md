# Public release checklist

The benchmark remains `draft` until every required item is complete.

## Dataset

- [ ] At least 100 unique frozen descriptions from LinkedIn and 100 from
  EURAXESS, with a documented sampling frame and no query leakage into the test
  split.
- [ ] Every supported enrichment path has audited positive and hard-negative
  coverage for each source, or is explicitly listed as out of scope.
- [ ] No exact or near duplicate crosses development and held-out test splits.
- [ ] Every public description has a documented redistribution basis; no
  private data, applicant data, credentials, or unnecessary personal data.
- [ ] Every text, case, split, schema, and manifest has an immutable digest.

## Ground truth

- [ ] Reviewers pass a frozen, human-authored qualification set with the
  thresholds and critical-error rules in `HUMAN_REVIEW_PLAN.md`.
- [ ] Two independent human reviews per scored label, blind to Actor output.
- [ ] Disagreements adjudicated and recorded.
- [ ] Pseudonymous first-pass labels are retained, and initial agreement,
  normalized-value agreement, adjudication, ambiguity, sentinel accuracy, and
  reviewer exclusions are reported by source and path.
- [ ] All scored labels are `gold_human_verified`; ambiguous labels are excluded.
- [ ] Evidence offsets, accepted values, initial-null eligibility, and protected
  static paths pass mechanical validation.
- [ ] Positive and negative prevalence is reported rather than hidden by one
  pooled percentage.
- [ ] Every external review service has documented processing rights, privacy,
  retention, deletion, and benchmark-publication compatibility.

## Runs

- [ ] Exact Actor ID, build number, immutable build ID, input, accuracy mode,
  run ID, dataset ID, timestamp, and benchmark digest recorded.
- [ ] At least three complete repeats per Actor and accuracy mode.
- [ ] No prompt, model, provider, routing, or code selection is made using the
  held-out labels.
- [ ] Dataset rows, completed records, failed records, and charged enrichment or
  translation events reconcile.
- [ ] Provider-heavy arms run sequentially and remain within the approved spend
  cap so production service credit is protected.

## Reporting

- [ ] Final `nomad-agent-job-v1` records are scored, not intermediate responses.
- [ ] LinkedIn/EURAXESS and Silver/Gold results are separate.
- [ ] Exact precision, recall, F1, specificity, unsupported-fill rate,
  case-field accuracy, static preservation, provenance integrity, and failure
  rate are reported with denominators and confidence intervals.
- [ ] Translation reports human adequacy/fluency, automated reference score,
  invariant preservation, and unchanged out-of-scope fields.
- [ ] Limitations, excluded cases, failed runs, and all post-freeze changes are
  disclosed.
- [ ] The package validates from a clean checkout with only documented public
  dependencies.
