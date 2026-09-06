# Contributor instructions

This repository publishes integration assets for normalized job-search Actors.

- Keep `nomad-agent-job-v1` as the canonical output. Never change an Actor's
  output contract merely to accommodate a table-oriented integration.
- Put table-oriented fields in the versioned `nomad-agent-flat-job-v1`
  projection and document any information loss.
- Preserve source semantics: `null` means unknown and `[]` means explicitly
  empty. Only named people belong in `hiringContacts`.
- Treat static extraction, description-derived facts, normalized data, LLM
  metadata, and raw source material as distinct layers.
- Deduplicate across sources with `jobKey = source:externalId`; do not use title
  or company as identity.
- Never commit credentials, private datasets, or real applicant data.
- Keep examples bounded and inexpensive. Optional translation, enrichment,
  analytics, and cross-run dedupe must remain explicit.
- Update schemas, examples, scripts, tests, and client instructions together.
- Run `python3 -m unittest discover -s tests -v` and validate every changed
  Agent Skill before committing.
- Do not claim a workflow is live-validated unless it was tested against the
  deployed Actor and the named destination platform.

- Maintained Actor callers select `latest`. Verify the immutable build ID and
  build number returned by each exact run; never require a historical numeric
  build selector. Preserve schema, source, count, retry, and cost validation.
