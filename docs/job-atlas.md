# Job Atlas releases

[Job Atlas on Apify](https://apify.com/job-atlas) is the current customer-facing home for these four Actors. The website remains [nomadagent.dev](https://nomadagent.dev/) and this repository keeps its existing GitHub address.

| Actor | Store | Website guide |
| --- | --- | --- |
| LinkedIn | [Run Actor](https://apify.com/job-atlas/linkedin-enrich-translate-normalize-scraper) | [LinkedIn guide](https://nomadagent.dev/actors/linkedin) |
| EURAXESS | [Run Actor](https://apify.com/job-atlas/euraxess-enrich-translate-normalize-scraper) | [EURAXESS guide](https://nomadagent.dev/actors/euraxess) |
| Y Combinator | [Run Actor](https://apify.com/job-atlas/ycombinator-enrich-translate-normalize-scraper) | [YC guide](https://nomadagent.dev/actors/ycombinator) |
| AI Job Fit Scorer | [Run Actor](https://apify.com/job-atlas/ai-job-fit-scorer) | [Scorer guide](https://nomadagent.dev/actors/ai-job-fit-scorer) |

## Client migration

New Store links, Actor identifiers, REST endpoints, MCP examples, skills, and workflow starters target Job Atlas. Start runs through `latest`, then retain and verify the returned immutable build ID and build number. Existing saved Tasks and imported workflows do not migrate themselves: create a Task for the corresponding Job Atlas Actor and replace its Task ID in your integration. Keep credentials in your integration platform.

The organization change does not rename `nomad-agent-job-v1`, `nomad-agent-flat-job-v1`, or scorer schemas. Those remain data contracts. It does not change source sites, optional feature costs, or the meaning of unknown fields.

## Evidence boundaries

The Job Atlas publication has bounded Actor execution proof: two normalized jobs per source and one synthetic supplied-job AI fit result. Optional enrichment, translation, all search adapters, hosted MCP, external template imports, named destination writes, and natural schedules have not been verified for this organization.

Older reports, example run receipts, integration evidence manifests, and numeric builds in the documentation describe their original primary-organization execution. They are historical evidence, not Job Atlas release numbers or proof of destination delivery after migration. Updated starters have local validation; test your own destination before relying on delivery.
