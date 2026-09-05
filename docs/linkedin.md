# LinkedIn Jobs Scraper | AI Enrichment

Get LinkedIn jobs ready for alerts, job boards, and spreadsheets. Search by role
and location, keep full descriptions and original job links, and skip jobs
already returned by earlier runs. Add AI enrichment or English translation when
you need them.

## Why choose this Actor?

- **Less cleanup:** consistent fields for titles, companies, locations, salaries,
  skills, and application links, when available.
- **Fewer repeat alerts:** built-in deduplication remembers jobs already delivered
  for the same search.
- **More useful details:** optional AI reads descriptions to fill missing facts
  without replacing source data.
- **Ready to connect:** export results or use the API, n8n, Make, Airtable, and MCP.

## Start with a small search

1. Enter a **Job keyword** and **Location**.
2. Set **Maximum results** to **5** and leave **First-run mode** and **Add company details** off for a basic search. Clear any **Company filters** already in the form.
3. Set Apify's **Maximum cost per run** to **$0.10**, then click **Start**.
4. Open the results to review the jobs and export your data.

AI enrichment and translation are optional paid extras. The cost cap can reduce
or stop output; the **Pricing** tab is authoritative for current charges.

Want to try the extras? Enable **First-run mode** for up to five jobs with Silver
AI enrichment and selected-field English translation. It keeps your search and
filters, disables deduplication and analytics, and omits descriptions from the
output. Turn it off again to use your own settings.

## Choose your results

| Setting | Default / option | What it does |
|---|---|---|
| Job keyword / Location | — | Search for a role or skill in a city, region, or country. An empty location searches worldwide. |
| Posted within | — | Choose how recent the jobs should be. Default: past 24 hours. |
| Work arrangements | — | Select remote, hybrid, on-site, or any combination. Leave empty for all. |
| `maxItems` | `100` | Maximum jobs returned; up to 1,000 per run. `0` requests that limit. |
| Result order | — | Newest or oldest first. |
| Cross-run deduplication | — | Skip jobs already delivered. Turn off for repeatable one-off searches. |
| Include descriptions | — | Keep full text and HTML in `raw`. Turn off for smaller exports. |

For separate alerts, use separate deduplication keys. An empty key keeps history
separate for each search; reusing a named key shares history across those searches
within your account. Duplicate tracking is bounded, so it is not permanent history.

Advanced controls support up to eight searches per run, job-field filters, strict
location checks, and company filters. Use the examples in the input form's JSON
editors. Clear the main keyword and location when providing multiple searches.

## Optional extras

- **AI enrichment:** fills supported missing fields from the job description.
  Silver is the standard tier; Gold adds a second check. Use Silver until Gold
  appears in the current Pricing table. AI can make mistakes; review important facts.
- **English translation:** translates selected job fields, including titles,
  requirements, and benefits. Full descriptions, company names, locations, skills,
  and URLs stay in their original form.
- **Company details:** adds available facts from the job's linked public company
  page, with no separate result-event charge. Company filters require this option.
  Unavailable profiles are excluded by default when company filters are used.

## What you get

Each job has its LinkedIn ID and URL, structured job details, optional company
facts and AI status, and the full description when requested. Missing facts remain
unknown; the Actor does not guarantee that every field will be filled.

The JSON format is `nomad-agent-job-v1`: `identity`, `data`, `custom`, `llm`,
`raw`, and `schemaVersion`. `null` means unknown; `[]` means confirmed empty.
A matching workplace search can still return an unknown per-job arrangement.
Sanitize source HTML before displaying it.

## Use the API or an integration

```python
from decimal import Decimal
from apify_client import ApifyClient

client = ApifyClient("<YOUR_APIFY_TOKEN>")
run = client.actor(
    "nomad-agent/linkedin-enrich-translate-normalize-scraper"
).call(run_input={
    "schemaVersion": "nomad-agent-job-search-input-v1",
    "keyword": "software engineer",
    "location": "Spain",
    "maxItems": 5,
    "firstRunMode": False,
    "aiEnrichment": {"enabled": False, "accuracy": "silver"},
    "translateToEnglish": False,
    "companyProfileEnrichment": False,
    "analyticsEnabled": False,
    "dedupe": {"enabled": False, "key": ""},
}, build="latest", max_items=5, max_total_charge_usd=Decimal("0.10"))

if not run["buildNumber"].startswith("1.0."):
    raise RuntimeError("unexpected Actor build")

for job in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(job["data"]["title"], job["identity"]["url"])
```

This standalone example follows `latest`. Check the [current default build API](https://api.apify.com/v2/acts/nomad-agent~linkedin-enrich-translate-normalize-scraper/builds/default)
for the default build number and immutable ID. Maintained integration templates
use their own tested exact pins; follow the selected template's compatibility
guide when running it. A `1.0.x` check alone does not prove compatibility.

[Integration guides and templates](https://github.com/Exdenta/nomad-agent-job-scrapers)
cover MCP, n8n, Make, Airtable, and agent skills.

## Pricing and limits

You pay per returned job, plus applicable translation and successful AI-enrichment
charges. Check the **Pricing** tab for current rates and scheduled changes.

Results depend on available public LinkedIn postings. Filters, source restrictions,
and your budget can reduce the count. Large searches take longer. Check
`RUN-SUMMARY` for the returned count, limits, and any retry suggestion; check
`llm.status` for each job's AI outcome. Strict location and company filters can
exclude jobs with missing evidence.

This independent Actor is not affiliated with or endorsed by LinkedIn.
Contact the Actor creator through the Apify issue tab for help or privacy requests.
For corrections or removal, include the job URL or ID and avoid private information.
