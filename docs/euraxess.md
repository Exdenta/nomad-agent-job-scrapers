# EURAXESS research and academic jobs

[`nomad-agent/euraxess-enrich-translate-normalize-scraper`](https://apify.com/nomad-agent/euraxess-enrich-translate-normalize-scraper)
finds public EURAXESS PhD, postdoctoral, fellowship, research, and faculty
vacancies and returns the shared `nomad-agent-job-v1` contract.

This integration pack supports exact build `1.0.13`. Pin that build in API,
MCP, n8n, and Make clients, and verify it on the completed run before accepting
results.

## Customer-visible features

- keyword and location search;
- multilingual keyword matching through the closed `euraxessSearch` option;
- research domains, seniority, requirements, funding, deadlines, contacts, and
  application details when published by the source;
- source-neutral normalized filters and explicit workplace filters;
- optional selected-field English translation and Silver or Gold enrichment;
- optional cross-run deduplication and aggregate analytics;
- canonical nested output plus the shared flat projection for table tools.

`postedWithin` accepts `24h`, `7d`, `30d`, or `any`. EURAXESS publication dates
do not include a posting hour, so `1h` is unsupported. Cutoffs use inclusive UTC
calendar dates: `24h` includes the current and previous UTC date, while `7d`
and `30d` include the date 7 or 30 days before the run.

EURAXESS `Positions` or `Academic Level` is source taxonomy, not an applicant
education requirement. A location is not workplace evidence. Only named people
are hiring contacts. `null` means unknown or unavailable; `[]` means the source
established that the collection is empty.

## Agent Skill

The complete
[`euraxess-enrich-translate-normalize-scraper`](../.agents/skills/euraxess-enrich-translate-normalize-scraper/SKILL.md)
skill includes:

- the strict [input reference](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/input-contract.md);
- the normalized and custom [output reference](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/output-contract.md);
- [MCP client setup](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/client-setup.md);
- bounded [search examples](../.agents/skills/euraxess-enrich-translate-normalize-scraper/references/search-examples.md);
- dependency-free validators, parsers, and the shared flat projection.

Install it into another project with:

```bash
python3 scripts/install_skill.py \
  --skill euraxess-enrich-translate-normalize-scraper \
  --client both \
  --target /path/to/project
```

## Integration artifacts

- [n8n to Google Sheets](../integrations/n8n/euraxess-jobs-to-google-sheets.json)
- [Make to Google Sheets](../integrations/make/euraxess-jobs-to-google-sheets.blueprint.json)
- [MCP arguments](../integrations/mcp/examples/euraxess-search.mcp.json)
- [REST API and webhook guidance](../integrations/api/README.md)
- [Airtable destination preset](../integrations/airtable/README.md)

The n8n and Make assets require terminal success, exact build `1.0.13`, a
valid `nomad-agent-run-summary-v4`, and a dataset row count equal to
`RUN-SUMMARY.delivered`. They preserve the canonical dataset and derive only
the documented flat view for Google Sheets. Importing a template never adds
credentials or activates a schedule.
