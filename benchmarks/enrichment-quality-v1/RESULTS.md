# Benchmark status and current evidence

Status: **draft — no official public score yet**
Evidence reviewed: 2026-08-15

## What the existing evidence supports

The saved LinkedIn challenge-set evaluation showed strong recovery of known
positive description facts for the selected Silver configuration: 352 of 354
positive case-fields across three repeats (99.44%), with contract-valid model
responses in every call. The selected Gold cascade recovered 117 of 118
positive case-fields (99.15%) in one run.

Those numbers are useful internal regression evidence, but they are not the
public benchmark result:

- labels were AI-assisted and adjudicated, not independently human verified;
- the negative labels were not fully re-audited and some are known to conflict
  with their source text;
- the challenge set is LinkedIn-only and deliberately enriched for positives;
- it covers a limited field set rather than every AI-eligible production path;
- it scored an intermediate semantic extraction format, not exact final Actor
  records; and
- one accepted location label maps to a production path that the evaluated
  grouped enrichment path does not request.

The old mixed diagnostic was 603/651 (92.63%) for Silver, including 251/297
nominal negatives (84.51% specificity). Because the negative labels are known
to be unreliable, these values must not be presented as hallucination or
population-accuracy claims.

## Operational evidence is not semantic accuracy

A prior 100-row LinkedIn canary completed Silver enrichment for 98 rows and
failed safely for two. It demonstrated delivery, charging, and fail-open base
records, but it did not independently verify whether the filled values were
correct.

There is currently no equivalent source-specific semantic benchmark for
EURAXESS. English translation has successful runtime and billing evidence, but
no frozen human-reference adequacy or fidelity score. Therefore neither an
EURAXESS accuracy percentage nor a translation-quality percentage is currently
defensible.

## First publishable result

The first official release will report:

- LinkedIn and EURAXESS separately;
- Silver and Gold separately;
- at least three exact repeats per mode;
- micro exact precision, recall, F1, specificity, unsupported-fill rate, and
  exact case-field accuracy;
- per-path denominators and scores;
- static-value preservation and `llm.filledFields` integrity;
- completion/failure rates from exact final Actor outputs;
- translation human adequacy/fluency plus automated reference and invariant
  checks; and
- confidence intervals with the immutable dataset, scorer, Actor build, and
  result digests.

No headline will say “99% accurate” unless its denominator, source, mode,
metric, confidence interval, and human-label status appear beside it.
