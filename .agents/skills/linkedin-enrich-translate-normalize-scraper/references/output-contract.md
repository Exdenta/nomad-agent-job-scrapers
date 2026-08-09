# LinkedIn normalized output

Target schema: `nomad-agent-job-v1`.

## Envelope

The top-level key set is closed and exact:

```json
{
  "schemaVersion": "nomad-agent-job-v1",
  "identity": {},
  "data": {},
  "custom": null,
  "llm": {},
  "raw": null
}
```

For LinkedIn, `identity.source` is `linkedin` and `custom` is `null`.

## Identity

- `identity.externalId`: LinkedIn's source-owned job ID when available.
- `identity.url`: canonical LinkedIn posting URL.
- Use `source:externalId` as cross-source dedupe identity.

## Normalized data

`data` contains:

- `title`
- `company`: name, source ID, department, company URL, logo URL
- `classification`: industries and job functions
- `domains` and `domainsRaw`
- `locations`: one or more structured location objects
- `employment`: workplace arrangements, applicant location constraints,
  schedules, contract types, duration, hours, and start date
- `application`: posting date, deadline, reference, applicant snapshot,
  external application URL/email, direct-apply flag and raw method label,
  point-in-time availability evidence, named hiring contacts, eligibility
  criteria, and selection process
- `seniority`: source labels and normalized levels
- `requirements`: education paths, experience, languages, required/preferred
  skills, certifications, and source qualification prose
- `benefits`
- `funding`
- `compensation`
- `constraints`: visa sponsorship, work authorization, security clearance, and
  location preference

Missing values remain `null`. An explicit empty list remains `[]`.

## LLM metadata

`llm.status` is `not_requested`, `completed`, or `failed`. Requested and filled
paths are recorded separately. Provider/model/prompt/completion provenance is
metadata; the filled facts live in `data`.

Static source values always win. Optional enrichment fills only null fields.

## Raw source

When `includeRaw` is true:

```json
{
  "description": "complete plain text",
  "descriptionHtml": "<p>complete source HTML</p>"
}
```

When it is false, the entire top-level `raw` value is `null`. Consumers must
handle both shapes.
