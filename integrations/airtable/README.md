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

In n8n, Make, or custom code, insert the incoming `jobKey` rather than the
example value. Do not deduplicate by title, company, URL, or Airtable record
ID.

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

