# Annotation guide

## Unit of judgment

Annotate one frozen description and one exact production `data.*` path at a
time. Judge only what the description explicitly says. Do not use the job
title, employer reputation, source metadata, location metadata, or outside
knowledge unless that text is part of the frozen description.

The deterministic pre-enrichment record is part of the case. A field is
AI-eligible only when its exact production path is `null` before enrichment.
An empty array means the source established that the collection is empty; it is
not interchangeable with unknown `null`.

## Labels

- `present`: the description explicitly supports a complete normalized value
  for the path. Include one or more accepted complete values and the smallest
  sufficient verbatim evidence spans.
- `absent`: a complete scan finds no support for the path. Accepted values and
  evidence must be empty.
- `ambiguous`: reasonable independent annotators cannot map the wording to one
  contract value without inference. State the ambiguity; the scorer excludes
  it from accuracy.

Values are complete replacements for the path, not isolated fragments. Keep
required and preferred skills separate, preserve modality, keep array facts
atomic, preserve source language, and do not silently normalize away meaningful
conditions.

## Evidence

Evidence uses zero-based character offsets into the exact frozen text. The
substring at `[start:end]` must equal `quote`. Include every span needed to
support the accepted value, but avoid unrelated surrounding prose.

An annotation tool or validator must mechanically verify the text digest,
offsets, quotes, production paths, accepted-value types, and initial-null
eligibility before review.

## Independent review

Official labels require:

1. two independent human annotations made without seeing Actor predictions;
2. disagreement adjudication by a third qualified reviewer or a documented
   consensus meeting;
3. a final `gold_human_verified` label with reviewer count and adjudication
   status;
4. a held-out test split that was not used to choose prompts, models, routing,
   thresholds, or field grouping.

Preserve the two pseudonymous first-pass labels and their rationales before
adjudication. The public GT quality report must disclose agreement,
disagreement, adjudication, ambiguity, and reviewer-exclusion rates by source
and path. See `HUMAN_REVIEW_PLAN.md` for qualification and pilot gates.

AI-assisted candidate generation is allowed for recruitment, but model
agreement is not human ground truth. Reviewers must inspect every final positive
and negative label.

## Negative cases

Negative cases are first-class. Recruit hard negatives containing nearby but
non-qualifying language, such as duties mistaken for required skills, company
certifications mistaken for candidate credentials, a bare office address
mistaken for onsite work, or the language of the advertisement mistaken for a
candidate language requirement.

Each scored path should have enough independently audited positive and negative
cases per source. Do not reuse one description excessively across fields; report
both case-field and unique-description denominators.

## Translation track

Translation labels cover only the Actor's declared translation paths. Each item
contains the source string, at least two independent English references for an
official release, and exact invariants that must survive unchanged. Human
reviewers rate adequacy and fluency separately; automated character F-score is a
reproducible secondary metric, not a substitute for human judgment.

Descriptions, company names, raw payloads, provenance, and fields outside the
declared translation allow-list must remain unchanged.
