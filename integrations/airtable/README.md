# Airtable preset: normalized jobs

This preset creates one reusable `Jobs` table for the 32-column
`nomad-agent-flat-job-v1` projection. It is intentionally destination-only:
the Actor keeps returning the canonical nested `nomad-agent-job-v1` record.

## Files

- `airtable-jobs-import.xlsx` — import-ready workbook with the `Jobs` headers
  and a `Field Setup` reference sheet.
- `airtable-fields.json` — field order, Airtable types, descriptions, and
  select options for reproducible setup.

## Create the table

1. In Airtable, create a base or open the destination base.
2. Choose **Add or import** -> **Microsoft Excel** and select
   `airtable-jobs-import.xlsx`.
3. Import the `Jobs` worksheet and use its first row as field names.
4. Rename the table to `Jobs` if Airtable used another name.
5. Configure the field types from the workbook's `Field Setup` sheet or
   `airtable-fields.json`.
6. Keep `jobKey` as the primary field. It is the stable identity
   `source:externalId`.

The workbook contains no real applicant data or credentials. Its example row
is clearly marked and should be deleted after Airtable has inferred the field
types.

## Duplicate detection and upsert

For every flat job row:

1. Search the `Jobs` table for the exact `jobKey`.
2. If one record is found, update that record with all 32 fields.
3. If no record is found, create a record with all 32 fields.
4. Treat more than one match as a data-quality error; merge or remove the
   duplicate before continuing.

Use this Airtable formula in a **Find records** or **Search records** step,
after safely escaping any single quote in the incoming key:

```text
{jobKey} = 'linkedin:4446226935'
```

For EURAXESS the same rule produces keys such as:

```text
{jobKey} = 'euraxess:452297'
```

In n8n, Make, or custom code, insert the incoming `jobKey` rather than the
example value. Do not deduplicate by title, company, URL, or Airtable record
ID.

The source single-select preset includes both `linkedin` and `euraxess`.
EURAXESS-specific research, funding, education, language, and application
evidence remains in the canonical nested record; the 32-column destination
view does not attempt to flatten every `custom` field.

All current LinkedIn `latest` and EURAXESS `latest` search features remain
available in the upstream n8n, Make, MCP, or API runner. Airtable receives the
result projection only, so input features need no Airtable-specific mapping.
Keep the canonical Actor dataset (or a separately access-controlled serialized
record) whenever downstream work needs nested source evidence, provenance,
source extensions, or raw content that the 32 fields do not contain.

## Upstream run boundary

This Airtable preset is destination-only. The n8n, Make, MCP, or API workflow
feeding it must require terminal success, the exact build, a valid minimal v4
`RUN-SUMMARY`, the hard one-retry bound, and a reconciled default dataset
before writing rows. See the
[shared run-completion policy](../../docs/retry-contract.md).

## Field choices

- URL fields use Airtable's URL type.
- `directApply` uses a checkbox.
- salary amounts use numbers.
- dates use date fields; enable time for `postedAt` when your source provides
  it.
- `llmStatus` is a single select with `not_requested`, `completed`, and
  `failed`.
- array projections such as `workArrangements` remain long-text JSON strings.
  Do not convert them to multiple-select fields if downstream logic must
  preserve `null` (unknown) versus `[]` (explicitly empty).
- `descriptionText` is long text. Confirm the destination's retention and
  access policy before storing job descriptions.

## Validation boundary

The workbook, field metadata, order, and example values are checked against
the shared flat schema in repository tests. Creating an Airtable base and
running an authenticated upsert are user-specific steps because the preset
contains no Airtable credentials or base IDs.
