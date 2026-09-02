# Normalized job enrichment quality benchmark v1

This public benchmark measures the optional description-backed enrichment and
selected-field English translation produced by the normalized LinkedIn and
EURAXESS Actors. It scores the final `nomad-agent-job-v1` records that users
receive, not an intermediate model response.

The first public dataset is being prepared. Until `benchmark.json` is marked
`public_release`, the files in this directory define the contract and provide
synthetic examples; they are not an official accuracy result.

## What it measures

- exact value recovery on facts that are explicitly present;
- specificity on facts that are explicitly absent;
- wrong-value and unsupported-fill rates;
- preservation of deterministic source values;
- consistency of `llm.filledFields` with actual null-to-value changes;
- contract-valid completion and failure rates across repeated runs;
- results reported separately for LinkedIn and EURAXESS;
- English-translation reference similarity and preservation of names, numbers,
  URLs, email addresses, identifiers, and other declared invariants.

It does not measure search coverage, freshness, ranking, source availability,
or the prevalence of facts in all jobs.

## Files

- `benchmark.schema.json` — public dataset contract.
- `prediction.schema.json` — submission contract for final Actor records.
- `score.py` — dependency-free validator and scorer.
- `benchmark.sample.json` and `predictions.sample.json` — synthetic examples.
- `ANNOTATION_GUIDE.md` — human labeling and adjudication rules.
- `HUMAN_REVIEW_PLAN.md` — reviewer recruitment, service options, pilot design,
  qualification, and GT quality gates.
- `RESULTS.md` — current evidence and the boundary around publishable claims.
- `RELEASE_CHECKLIST.md` — gates for the first official release.

## Run the sample

```bash
python3 benchmarks/enrichment-quality-v1/score.py \
  benchmarks/enrichment-quality-v1/benchmark.sample.json \
  benchmarks/enrichment-quality-v1/predictions.sample.json

python3 benchmarks/enrichment-quality-v1/self_test.py
```

The scorer exits non-zero on a malformed dataset or submission. Use
`--output result.json` to save the machine-readable score.
For a `public_release` dataset it also loads the repository's source-specific
closed-contract validators and rejects any incomplete or malformed final
`nomad-agent-job-v1` record.

## Primary metrics

For each audited `data.*` case-field:

- a matching accepted value on a `present` label is a true positive;
- `null` on a `present` label is a false negative;
- a non-matching value on a `present` label is both a false positive and a
  false negative;
- `null` on an `absent` label is a true negative;
- a non-null value on an `absent` label is an unsupported fill.

The headline is micro exact precision, recall, and F1, accompanied by exact
case-field accuracy, absent-field specificity, unsupported-fill rate, static
preservation, contract completion, and per-source/per-path results. Ambiguous
labels are excluded, never forced into positive or negative classes.

## Reproducibility and rights

Every self-contained public case includes its exact text, SHA-256 digest,
redistribution basis, observation metadata, evidence spans, and label-review
provenance. A URL alone is not a frozen benchmark. Descriptions may be included
only when redistribution is permitted; otherwise the case cannot enter the
self-contained public score set.

Official results must identify immutable Actor build IDs, exact build numbers,
benchmark digest, accuracy mode, repeat count, and scorer version. Results for
different sources, builds, modes, or dataset versions are never silently
pooled.
