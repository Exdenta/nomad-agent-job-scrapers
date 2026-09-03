# Nomad Agent SEO program

This document is the operating contract for growing
[nomadagent.dev](https://nomadagent.dev/) without weakening product accuracy,
privacy, or release-proof boundaries. It covers the first 90 days after the
expanded site launch and remains useful as the recurring review checklist.
The pre-expansion state is preserved in the
[2026-09-03 SEO baseline](seo-baselines/2026-09-03.md).

## Positioning

**For** developers, automation builders, recruiters, and job-search product
teams who need source-linked job data, **Nomad Agent Job Data** is a set of
job-data APIs, integration packs, and AI matching tools that preserve identity,
provenance, and failure state. **Unlike** copying search-result rows into an
unversioned table, the project publishes bounded inputs, versioned contracts,
exact-build checks, and explicit delivery boundaries.

The public message has three pillars:

1. **Collect dependable job data.** Search LinkedIn or EURAXESS with bounded
   inputs and retain the original listing identity.
2. **Automate without erasing semantics.** Deliver canonical or documented flat
   records through n8n, Make, MCP, REST, Airtable, or Python.
3. **Rank with evidence.** Score jobs against a candidate while retaining hard
   requirement checks, evidence, gaps, and unknowns.

Claims must come from the current repository contract, public Actor metadata,
or a dated live test. Never convert an Actor run, integration import, search
submission receipt, or synthetic benchmark into a stronger claim.

## Search-intent ownership

Each page owns one primary intent. Supporting guides answer adjacent tasks and
link back to one product page and one implementation page.

| Canonical path | Primary intent |
| --- | --- |
| `/` | Job-data APIs, automations, and AI matching |
| `/actors/linkedin` | LinkedIn jobs scraper API and normalized LinkedIn job data |
| `/actors/euraxess` | EURAXESS jobs scraper and research-jobs data API |
| `/actors/ai-job-fit-scorer` | AI job matching and job-fit scoring API |
| `/integrations/n8n` | n8n job-alert and job-tracker workflows |
| `/integrations/make` | Make job-data to Google Sheets automation |
| `/integrations/mcp` | Job search and scoring through Apify MCP |
| `/integrations/api` | Job scraper REST API and webhook integration |
| `/integrations/airtable` | Airtable job-tracker data model |
| `/integrations/python` | Python validation and projection of normalized jobs |
| `/integrations/zapier` | Zapier editor recipe for scored-job delivery |
| `/contracts` | Versioned normalized job and fit-score schemas |
| `/guides/linkedin-jobs-api-alternatives` | LinkedIn Jobs API alternatives |
| `/guides/linkedin-job-alerts-n8n` | Daily LinkedIn job alerts with n8n |
| `/guides/euraxess-jobs-api-export` | EURAXESS jobs API and export options |
| `/guides/ai-job-fit-scoring-api` | Implementing evidence-backed job-fit scoring |

Do not publish role/location combinations unless the site gains unique,
maintained inventory that lets each page answer a distinct search task.

## Measurement contract

The program evaluates search discovery, traffic, and product intent separately:

| Layer | Evidence | Decision use |
| --- | --- | --- |
| Deployment | Exact artifact and live HTTP checks | Confirms the intended site is live |
| Discovery | Sitemap and IndexNow receipts | Confirms notification only |
| Crawling/indexing | Google URL Inspection and Bing Site Explorer | Diagnoses per-URL search state |
| Demand | Search Console impressions, queries, clicks, and position | Chooses pages and topics to improve |
| On-site intent | Privacy-minimized CTA, copy, and workflow-download events | Compares landing-page usefulness |
| Product outcome | Attributable first successful run or verified destination | Measures activation only when available |

`scripts/search_performance.py` captures aggregate Search Console page/query
evidence. `.github/workflows/seo-observatory.yml` runs it weekly, omits raw query
text, and retains the page-level and branded/non-brand aggregates for 90 days.
It contains no cookies or session identifiers. An explicitly private local run
may retain query strings, but those are user-supplied text and must be reviewed
before any quotation or publication. Search Console can return top rows rather
than an exhaustive query set, so the artifact records that limitation described in the
[Search Analytics API documentation](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).
The existing indexing monitor remains the source for Google and Bing URL state.

Set numerical growth targets only after the first complete 28-day baseline.
Before that baseline, use these non-negotiable gates:

- every intended canonical page is crawlable and present in the sitemap;
- every public schema identifier resolves to the exact checked-in schema;
- no page is revised solely because it was unindexed for less than 72 hours;
- every content change has a query hypothesis and one measurable outcome;
- no customer, accuracy, conversion, or performance claim is published without
  dated evidence.

## 90-day execution cadence

### Days 1–14: integrity, catalog, and measurement

- Serve every public contract identifier and publish the contracts hub.
- Align the website with all three products and every supported integration.
- Give the homepage a customer-outcome title, H1, and three-path product model.
- Add Actor, integration, guide, About, methodology, privacy, and changelog hubs.
- Instrument consistent semantic events on every CTA and copy/download action.
- Verify live canonicals, indexability, content type, and deployed bytes before
  notifying search engines.
- Record the 72-hour, seven-day, and fourteen-day indexing states without blind
  resubmission.

### Days 15–45: task-complete pages and distribution

- Expand product and integration pages with real bounded examples, output,
  limitations, cost boundaries, troubleshooting, and dated proof.
- Publish the four intent-led guides in the table above.
- Link the canonical website from the GitHub repository, public Actor pages,
  and any owned n8n or Make template listing.
- Pursue documentation and integration-directory links by publishing useful
  runnable assets, not generic guest posts or paid link placements.

### Days 46–90: evidence-led iteration

- Compare page/query evidence at 28, 56, and 84 days.
- Improve pages with impressions but weak click-through before creating more
  URLs; improve task completion and differentiation where pages are crawled but
  remain unindexed.
- Check query overlap before splitting or merging pages.
- Invite design partners to a documented, consent-based case-study process.
- Publish a case study only after the customer approves the wording and its
  measurable outcome can be independently supported.

## Weekly review

1. Read the latest indexing monitor state and weekly evidence artifact.
2. Separate branded from non-branded demand.
3. Map each material query to the canonical intent owner above.
4. Choose at most three changes with a stated hypothesis.
5. Run repository tests, deploy the exact approved artifact, and verify live
   parity before recording the result.
6. Update the public changelog only with deployed, independently checked facts.

## Case-study evidence template

Do not create a placeholder testimonial. Use the
[case-study evidence template](case-study-evidence-template.md) for a real
design partner and retain only:

- the customer's approved public name and role;
- the initial workflow and bounded comparison period;
- a reproducible definition for each outcome metric;
- the exact Actor and integration versions used;
- limitations, exclusions, and who performed verification;
- written approval for the final public wording.

If any item is missing, keep the evidence private and describe the work as a
design-partner test rather than a customer result.
