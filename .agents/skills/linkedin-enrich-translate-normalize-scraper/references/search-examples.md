# Search examples

Keep the first run small. These prompts assume the skill and Apify MCP server
are already installed and authorized.

For every search, use generic `call-actor` with exact build `0.6.48`, poll a
non-terminal run with `get-actor-run`, and verify the authoritative run build.
Only after `SUCCEEDED` with exit code 0, fetch that run's default dataset with
`get-dataset-items` and paginate when necessary. An empty successful dataset
is valid. A failed, timed-out, aborted, or wrong-build run is an error; never
present its partial rows as success or start an automatic paid retry.

## Focused search

```text
Search LinkedIn for TypeScript developer jobs in Spain posted in the last 7
days. Include remote and hybrid jobs and return at most 5. Keep translation,
AI enrichment, analytics, and cross-run dedupe off. Fetch the complete dataset,
validate nomad-agent-job-v1, and show title, company, location, work
arrangement, posting date, and links. If the successful dataset is empty, say
that no matching jobs were returned.
```

## Remote search with unknown-safe output

```text
Find up to 5 remote data engineer jobs in the European Union posted in the
last 24 hours. Do not infer remote status, seniority, salary, or work
authorization when a field is missing. Preserve null as unknown and [] as a
known-empty list in the canonical records.
```

## Larger search after confirmation

```text
First inspect the Actor's current pricing and input schema. Then ask me before
running a 50-item search for product designer jobs in the United States posted
in the last 30 days. Leave translation and AI enrichment off. Do not retry an
ambiguous timeout automatically.
```

## Table export

```text
Search for up to 5 Python developer jobs in Madrid posted in the last 7 days.
Retain the complete normalized records, then use the bundled flat projection
only for a table export. Deduplicate the table with jobKey, which is
source:externalId, not title or company.
```

## Stateful alert

```text
Explain the cross-run dedupe scope and reset acknowledgement before enabling
it for this specific alert profile. Do not use a global account-wide key. Run
only after I confirm the stable opaque profile key and the extra stateful
behavior.
```
