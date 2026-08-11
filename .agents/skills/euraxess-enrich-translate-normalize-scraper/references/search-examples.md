# EURAXESS search examples

These are bounded contract examples for a future compatible `1.0` deployment.
The current private Actor is an older `0.5.1` build, so an agent must inspect
the deployed schema and stop rather than execute when it differs.

## Focused research search

```text
After confirming the deployed Actor accepts nomad-agent-job-search-input-v1,
search EURAXESS for up to 5 postdoctoral machine-learning positions in Germany
posted within 30 days. Disable cross-run dedupe, translation, enrichment, and
analytics. Fetch the complete successful dataset, validate nomad-agent-job-v1,
and show title, organisation, research domains, location, explicit workplace
arrangement, posting deadline, and links. A successful explicit-empty result is
valid.
```

## Source-taxonomy-safe search

```text
Find up to 5 PhD positions on EURAXESS. Preserve Positions / Academic Level
labels in custom.data.academicLevelRaw. Do not convert them into education
requirements unless an explicit Education Level row independently establishes
that requirement. Preserve null versus [].
```

## Multilingual keyword expansion

```text
Explain the deployed price and owner-managed provider boundary first. If I
confirm, enable euraxessSearch with schemaVersion
nomad-agent-euraxess-search-v1 and translateKeywords true for the exact keyword
"computational biology". Retain the original keyword, do not broaden the
discipline, and leave output translation and position enrichment off.
```

## Explicit workplace constraint

```text
Search for up to 5 EURAXESS roles explicitly marked remote or hybrid. Unknown
work arrangements must not match. Never infer onsite, hybrid, or remote from a
country, city, facility, address, or narrative preference.
```

## Table export

```text
Retain the complete validated EURAXESS records, including custom, requirements,
named contacts, availability evidence, and provenance. Then create a separate
nomad-agent-flat-job-v1 table projection. Deduplicate on source:externalId,
not title or organisation.
```

## Stateful alert

```text
Explain tenant/query scope and replayEpoch before enabling cross-run dedupe for
this specific alert. Ask me to confirm one stable opaque profile key. Do not
share a global account-wide key across unrelated alerts or users.
```
