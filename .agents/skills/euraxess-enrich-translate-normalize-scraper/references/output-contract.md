# EURAXESS normalized output

Target schema: `nomad-agent-job-v1`.

## Closed envelope

Every item has exactly:

```json
{
  "schemaVersion": "nomad-agent-job-v1",
  "identity": {},
  "data": {},
  "custom": {},
  "llm": {},
  "raw": null
}
```

For this Actor, `identity.source` is `euraxess`. `identity.externalId` is the
source-owned EURAXESS node ID when established and `identity.url` is the
canonical posting URL. Use `source:externalId` as the primary cross-source
identity; retain the canonical URL as fallback evidence when an ID is absent.

## Common normalized facts

`data` contains the complete common contract:

- title and organisation/department;
- source classification, normalized domains, and raw domain paths;
- structured work locations and explicitly established workplace facts;
- contract, duration, hours, start-date, and schedule facts;
- posting/deadline/reference/application facts, evidence-backed availability,
  and named hiring contacts;
- EURAXESS researcher-profile seniority such as `R1` through `R4`;
- explicit education, experience, language, skill, certification, and
  free-text requirement facts;
- benefits, funding programme, compensation, and constraints.

`null` means unknown. `[]` means the source explicitly established an empty
collection. A location is never workplace-arrangement evidence. Only an
explicit education row belongs in `data.requirements.education`.

## EURAXESS custom extension

`custom` is not null. It has this closed shape:

```json
{
  "schemaId": "https://raw.githubusercontent.com/Exdenta/nomad-agent-job-scrapers/main/integrations/shared/euraxess-v1.schema.json",
  "data": {
    "academicLevelRaw": ["PhD Positions"],
    "researchInfrastructureStaffPosition": null,
    "unmappedJobInformation": null,
    "unparsedGeofields": null
  }
}
```

- `academicLevelRaw` preserves EURAXESS `Positions` / `Academic Level`
  taxonomy. It is not an applicant education requirement.
- `researchInfrastructureStaffPosition` preserves the source-specific label.
- `unmappedJobInformation` retains newly encountered labelled fields without
  guessing a common meaning.
- `unparsedGeofields` retains malformed geospatial source payloads instead of
  inventing coordinates.

The extension schema is separately versioned. Its public mirror is
[`integrations/shared/euraxess-v1.schema.json`](../../../../integrations/shared/euraxess-v1.schema.json),
which retains the canonical `$id`. Do not flatten these facts into unrelated
common fields.

## Contacts, application, and availability

Only a contact with a person's name may appear in
`data.application.hiringContacts`. An anonymous or generic email is an
application channel only when EURAXESS explicitly publishes it under `Where
to apply`; it is never a person. Emails found only in the EURAXESS `Contact`
block remain in `raw` evidence and are not promoted to `application.email` or
to a named hiring contact.

`identity.url` is the EURAXESS posting. `data.application.url` is populated
only when the source explicitly establishes a separate application
destination. Prose and generic contact links are not sufficient.

Availability requires timestamped evidence. A complete detail response can
establish availability; an explicit `404` or `410` can establish
unavailability. Blocking, errors, ambiguous shells, and absence from one
search do not prove closure.

## LLM and raw layers

`llm.status` is `not_requested`, `completed`, or `failed`. Requested and filled
paths are recorded separately. Filled facts live in `data`; provider, model,
prompt, and completion values are provenance only. Static facts and
source-established empty arrays always win.

With `includeRaw: true`, `raw.description` and `raw.descriptionHtml` contain
the complete detail text and untrusted source HTML. With `includeRaw: false`,
the entire top-level `raw` value is `null`. A listing snippet is never promoted
to a complete description. Sanitize HTML before rendering it.
