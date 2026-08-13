# EURAXESS normalized Actor contract

`nomad-agent/euraxess-enrich-translate-normalize-scraper` targets public
EURAXESS PhD, postdoctoral, fellowship, research, and faculty vacancies.

This repository documents the strict `1.0` contract. The private Actor's
`latest` and `canary` tags point to exact build `1.0.10`. These contract files
describe expected inputs and outputs; they do not by themselves prove live
source or destination behavior.

## What is shared with the normalized fleet

- strict `nomad-agent-job-search-input-v1` caller envelope;
- exact six-root `nomad-agent-job-v1` output;
- source-neutral normalized filters;
- optional owner-managed selected-field translation;
- optional owner-managed Silver/Gold null-only enrichment;
- explicit cross-run dedupe and aggregate analytics controls;
- transactional delivery semantics in the Actor runtime.

## What remains EURAXESS-specific

- public search-card discovery and complete detail-page parsing;
- the closed `nomad-agent-euraxess-search-v1` multilingual keyword extension;
- researcher-profile seniority and research-domain paths;
- explicit education, language, experience, funding, location, and application
  labels found on EURAXESS details;
- `custom.data.academicLevelRaw`, research-infrastructure labels, unmapped
  labelled facts, and malformed geospatial fallback evidence;
- conservative contact, workplace, description, and availability semantics.
- calendar-date publication evidence: `postedWithin` accepts `24h`, `7d`,
  `30d`, or `any`, while `1h` is rejected because EURAXESS supplies no posting
  hour or timezone.

Freshness cutoffs are inclusive UTC dates rather than elapsed durations.
`24h` includes the current and previous UTC calendar date and can therefore
include records older than 24 elapsed hours. `7d` and `30d` subtract 7 or 30
UTC calendar days and include the resulting cutoff date; `any` has no cutoff.

In particular, EURAXESS `Positions` / `Academic Level` is board taxonomy, not
an applicant education requirement. A location is not workplace evidence.
Only named people are hiring contacts. A generic email is an application
channel only when explicitly published under `Where to apply`; `Contact`-block
emails remain raw and are not promoted. A listing snippet is not a complete
description. `null` and `[]` remain semantically distinct.

## Agent package

The complete skill is
[`euraxess-enrich-translate-normalize-scraper`](../.agents/skills/euraxess-enrich-translate-normalize-scraper/SKILL.md).
It contains:

- strict [input reference](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/input-contract.md);
- normalized and custom [output reference](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/output-contract.md);
- exact public mirror of the canonical
  [EURAXESS v1 custom schema](../integrations/shared/euraxess-v1.schema.json),
  retaining its canonical `$id`;
- MCP [client setup](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/client-setup.md);
- bounded [search examples](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/search-examples.md);
- dependency-free canonical job validator, parser, and shared flat projection.

Install it into another project with:

```bash
python3 scripts/install_skill.py \
  --skill euraxess-enrich-translate-normalize-scraper \
  --client both \
  --target /path/to/project
```

Before any live run, fetch Actor details and require the matching strict input
schema. Pin exact build `1.0.10`; do not rely on a movable tag in a client
integration.

## Integration artifacts

The public pack includes source-specific, credential-free, offline-tested
examples:

- [n8n to Google Sheets](../integrations/n8n/euraxess-jobs-to-google-sheets.json);
- [Make to Google Sheets](../integrations/make/euraxess-jobs-to-google-sheets.blueprint.json);
- [bounded MCP arguments](../integrations/mcp/examples/euraxess-search.mcp.json) and scoped OAuth configurations for Codex, Claude Code, and Cursor;
- [exact-build REST API and webhook guidance](../integrations/api/README.md);
- the shared [Airtable destination preset](../integrations/airtable/README.md), using `euraxess:<externalId>` as `jobKey`.

The n8n and Make assets require terminal success, exact build `1.0.10`, a valid
minimal v4 `RUN-SUMMARY`, the hard one-retry bound, and a default dataset
reconciled with `delivered`.
They preserve the canonical Actor dataset and derive only the documented
32-column flat view for Google Sheets. Importing an asset never supplies
credentials or activates a schedule. No EURAXESS destination-platform smoke
test has been completed yet.
