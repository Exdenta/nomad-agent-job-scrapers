# Human ground-truth review plan

Human labeling can materially improve this benchmark, but only when the
reviewers are qualified, independent, blind to Actor output, and required to
show exact textual evidence. A majority vote from an unqualified general crowd
is not gold ground truth.

This plan covers reviewer recruitment, qualification, assignment,
adjudication, quality reporting, and a bounded first pilot. It does not
authorize uploading source text to any vendor. Confirm redistribution and
third-party-processing rights, privacy terms, retention, and deletion before
sharing a description.

## Recommended approach

Use a small, reusable expert panel for the first release:

- two reviewers with recruiting, HR data, job-board, or job-normalization
  experience for general employment fields;
- two reviewers with research hiring, research administration, EURAXESS, or
  academic-career experience for EURAXESS-specific wording;
- bilingual reviewers for every language represented in the translation
  track, with strong English and native or near-native source-language skill;
- one senior adjudicator who did not create the Actor prediction being judged.

One person may qualify for more than one cohort, but the same two people should
not review every case. Rotate assignments so reviewer-specific bias can be
measured.

For the pilot, recruit through Prolific custom screening and run the task in a
benchmark-owned review application. Prolific supports custom screening and
reusable participant groups for niche populations, while the benchmark keeps
control of evidence offsets, null-versus-empty checks, and export format:

- [Prolific custom screening](https://researcher-help.prolific.com/en/articles/445155-how-to-use-custom-screening-to-recruit-specific-participants)
- [Prolific participant groups](https://researcher-help.prolific.com/en/articles/445158-participant-groups)

Prolific is a recruitment and payment layer, not a managed annotation program.
The benchmark owner remains responsible for training, task design, quality
control, adjudication, and audit exports.

## Current service options

These services can support this type of text labeling. Their fit differs.

| Service | Best fit here | Useful capabilities | Main caution | Recommendation |
| --- | --- | --- | --- | --- |
| Prolific | A bounded expert-panel pilot | Custom screening, allowlists, reusable participant groups, and external study tools | Not a managed labeling service; domain claims still need a qualification test | **Use first** for 30 LinkedIn and 30 EURAXESS descriptions |
| Appen | A larger multilingual managed program | Text/NLP annotation, calibrated contributors, independent review rounds, agreement measurement, and multilingual/domain-specialist pools | Quote-based enterprise engagement may be excessive for a small pilot | Strong managed-scale candidate after the protocol is stable |
| Labelbox managed services | A managed workforce plus annotation operations | Skilled workforce, project management, labeling workflows, and privacy controls | Confirm minimum engagement, export format, evidence-offset support, and data terms | Good enterprise alternative if its text task can preserve this schema exactly |
| AWS SageMaker Ground Truth / Ground Truth Plus | Teams already operating in AWS or needing a private workforce | Private, vendor, or public workforces; custom tasks; managed expert workforce in Ground Truth Plus | More setup; public workforce is appropriate only for public or PII-stripped data | Prefer for AWS-native or higher-control deployments, not the quickest pilot |
| Toloka | Self-service crowd or domain-expert annotation | Configurable annotation/evaluation tasks and expert/crowd workforces | Current self-service terms appear to restrict publishing benchmarks of non-open models or features | Do not use for this public benchmark without written confirmation that publication is permitted |

Official service descriptions:

- [Appen data annotation](https://www.appen.com/ai-data/data-annotation)
- [Labelbox managed services](https://docs.labelbox.com/docs/managed-services)
- [AWS Ground Truth workforces](https://docs.aws.amazon.com/sagemaker/latest/dg/sms-workforce-management.html)
- [AWS Ground Truth FAQ](https://aws.amazon.com/sagemaker/ai/groundtruth/faqs/)
- [Toloka self-service agreement](https://toloka.ai/legal/self-service-agreement)

Vendor claims are not benchmark evidence. Run the same hidden qualification
set and quality audit for every workforce, including a managed one.

## Qualification gate

Create a human-authored qualification set before recruiting production
reviewers. It must not be generated from Actor predictions.

1. Prepare 16 to 24 cases covering both sources, positive facts, complete-scan
   negatives, ambiguous wording, hard negatives, evidence spans, arrays,
   `null` versus `[]`, and source-specific academic wording.
2. Have two internal subject-matter reviewers and a third adjudicator freeze
   the qualification answers.
3. Require at least 90% correct present/absent/ambiguous decisions and at least
   85% exact normalized-value agreement.
4. Treat an unsupported inference, a static-value overwrite, or confusion of
   `null` and `[]` as a critical error. A reviewer with a critical error retrains
   and retakes a different qualification form.
5. Use pseudonymous reviewer IDs. Store screening claims separately from
   benchmark labels and publish no personal profile data.

The thresholds are initial operating gates, not claims that reviewers are 90%
accurate on the held-out benchmark.

## Annotation workflow

Each description is one whole-document task. Within it, the reviewer labels
every eligible production path. This is necessary because an `absent` judgment
requires a complete scan; isolated snippets are insufficient for negatives.

1. Freeze the exact description, SHA-256 digest, deterministic pre-enrichment
   record, and eligible null paths.
2. Randomize task order and hide source prevalence, Actor prediction, build,
   mode, price tier, and the other reviewer's answer.
3. Collect two independent first-pass annotations for every case-field.
4. Save each first-pass label before any discussion. Never replace the raw
   label with the consensus result.
5. Auto-accept exact agreement only after validating value types, evidence
   offsets, and evidence quotes.
6. Route disagreements to a third qualified adjudicator with both anonymized
   rationales but still no Actor prediction.
7. Mark genuinely under-specified text `ambiguous`; do not force it into the
   score.
8. Freeze final gold labels and split hashes before using test results for any
   prompt, model, routing, grouping, or threshold decision.

For translation, collect two independent English references and then have a
third bilingual reviewer rate adequacy and fluency and adjudicate material
meaning differences. Preserve declared names, numbers, identifiers, email
addresses, URLs, and other invariants exactly.

## Pilot specification

Start with a bounded protocol-validation pilot, not the full public release:

- 30 unique LinkedIn descriptions and 30 unique EURAXESS descriptions;
- source-stratified positive, absent, hard-negative, and ambiguous cases;
- every currently supported enrichment path reviewed in the whole-document
  task;
- two independent reviewers per description;
- 10% hidden sentinel tasks interleaved after qualification;
- 20 to 30 non-English translation items across the intended release
  languages, with two references and bilingual adjudication;
- no item from the future held-out test split used as qualification or sentinel
  material.

Expected enrichment effort is roughly 30 to 45 reviewer-hours if each
whole-document pass takes 10 to 15 minutes, plus translation review. Measure
actual completion time in the pilot before budgeting the 200-description
release.

As of August 2026, Prolific lists a 42.8% corporate platform fee on top of
participant rewards and recommends at least $12/£9 per hour. Domain experts
should be paid at a rate appropriate to their skill, not at the platform
minimum. For example, 40 reviewer-hours at $25 per hour is $1,000 in rewards
and approximately $1,428 before VAT after the listed corporate fee. This is a
planning example, not a vendor quote:

- [Prolific pricing](https://researcher-help.prolific.com/en/articles/445239-what-is-your-pricing)
- [Prolific participant-pay guidance](https://researcher-help.prolific.com/en/articles/445266-how-much-should-i-pay-participants)

Do not launch the full release until the pilot establishes actual task time,
reviewer availability, disagreement rates, and translation-language coverage.

## GT quality report

Publish the ground-truth process separately from Actor accuracy. At minimum,
report by source and path:

- reviewer count and cohort qualifications;
- initial categorical agreement and present/absent prevalence;
- exact normalized-value agreement;
- evidence-span exact agreement or overlap;
- disagreement and adjudication rates;
- hidden-sentinel accuracy and reviewer exclusions;
- ambiguous-label rate;
- translation adequacy, fluency, and invariant-preservation agreement;
- protocol version, instruction digest, anonymized first-pass labels, final
  labels, and every post-freeze correction.

Raw agreement and a chance-corrected statistic such as Cohen's kappa should be
reported together. Class imbalance can make kappa unstable, so neither number
should be used alone. Low agreement is a protocol problem to investigate, not
something to hide through majority voting.

## Pilot acceptance criteria

Proceed to the 100-per-source public release only when:

- all accepted reviewers pass the qualification gate;
- every scored label has two blind first-pass judgments;
- every disagreement is independently adjudicated;
- no critical null/empty, inference, or static-overwrite error remains;
- at least 85% initial categorical agreement is reached overall and no
  source-path cell with adequate sample size is below 75%;
- any path above 20% adjudication receives a guideline review and a fresh
  relabeling sample;
- the review export reproduces final labels without exposing personal data;
- every shared description has documented processing and redistribution
  rights;
- the held-out test split remains sealed.

These thresholds govern the annotation process. They do not replace the
benchmark's separate Actor-quality metrics or public-release checklist.
