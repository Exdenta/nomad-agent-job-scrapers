# CEO / Founder Public Information and Executive Report

**Subject:** Nomad Agent / NomadDev job-data products
**Prepared:** 2026-08-27 (Europe/Madrid)
**Scope:** Public founder/creator information, product portfolio, normalized
LinkedIn and EURAXESS Actors, positioning, traction, pricing, competition,
release state, trust, and the next executive decisions.

## Executive conclusion

The reviewed public evidence supports describing **Lex Sherman as a publicly
self-described founder and the creator behind the NomadDev / Nomad Agent
portfolio**. It does **not** establish a formal CEO title, legal company name,
incorporation, ownership, team size, funding, or revenue. Any biography should
therefore say “founder” or “creator,” not “CEO,” unless a first-party corporate
source is added.

The business has a credible technical foundation and a surprisingly broad
public footprint: the Apify creator profile reports 57 public Actors, 405 total
users, 198 monthly users, and a 92.9% run-success rate at the profile level.
However, the two normalized products covered by this repository remain
pre-traction in the public Store snapshots: each shows 2 total users, 1 monthly
active user, no bookmarks, and no reviews.

The immediate executive constraint is not product capability. It is the gap
between capability and trusted adoption:

1. local integration assets have moved to LinkedIn `1.0.2` and EURAXESS
   `1.0.16`, while the checked-out committed baseline still pins `0.6.48` and
   `1.0.13`;
2. the live immutable Actor builds and recent successful runs could not be
   refreshed in this audit;
3. public Store copy includes internal accuracy percentages while the public
   benchmark correctly says no official human-verified score exists yet;
4. the website contains attributable CTAs but no analytics collector by
   default, so visits, clicks, first runs, repeat use, and revenue cannot be
   reconciled; and
5. market leaders win with proof, reviews, tutorials, Tasks, and simple use
   cases, while Nomad Agent currently leads with a more technical contract
   story.

**CEO recommendation:** freeze broad feature expansion for this product line
until release state, claims, and measurement are reconciled. Keep base pricing
stable for now. Sell one outcome—duplicate-safe, source-linked job data for
recurring automations—and use the broader researcher bundle as the main
academic discovery product, with normalized EURAXESS as specialist
infrastructure.

## 1. Public founder and leadership information

### Confirmed public facts

| Fact | Public evidence | Confidence |
| --- | --- | --- |
| Name | GitHub profile identifies “Lex Sherman” | High |
| Public role language | GitHub bio says “Machine Learning / Data Analytics / Founder” | High |
| Creator identity | Apify profile `nomad-agent` is branded “NomadDev” and links directly to the same GitHub and LinkedIn profiles | High |
| Location | GitHub says Spain; Apify bio says Bilbao, Spain | High for public self-description, not independently verified |
| Experience claim | Apify bio says 10 years building ML, recommendation systems, demand forecasting, websites, and apps | Medium; self-described |
| Products named by the creator profile | Hesperia Market, Travel Eat, and OinkJobSearch | High |
| Founder corroboration | Travel Eat’s public page identifies Lex Sherman as its founder | High for Travel Eat |

Primary public sources:

- [NomadDev Apify creator profile](https://apify.com/nomad-agent)
- [Lex Sherman / Exdenta GitHub profile](https://github.com/Exdenta)
- [Travel Eat founder page](https://traveleat.app/)
- [Hesperia Market](https://hesperiamarket.eu/)

### Not established by the reviewed evidence

- no first-party source uses the title “CEO”;
- no legal entity, registration number, ownership structure, board, or formal
  executive team is disclosed;
- no founder biography appears on `nomadagent.dev`;
- no revenue, funding, salary, valuation, customer contracts, or employee count
  is public in the reviewed sources;
- the linked LinkedIn profile could not be read without encountering
  LinkedIn’s public-access block, so no facts were taken from it; and
- this was not a corporate-registry, litigation, credit, or legal due-diligence
  search.

### Identity and brand consistency risk

The same public footprint uses **NomadDev**, **Nomad.Dev**, **Nomad Agent**,
`nomad-agent`, and the personal GitHub namespace **Exdenta**. The links make the
relationship understandable, but the naming is not yet a clean company
identity. The product website also contains no About, Contact, Privacy, Terms,
Person schema, or Organization schema; its structured data describes only the
two software products.

There is a deliberate CEO choice to make:

- **Founder-led brand:** add a concise founder page, consistent name, public
  support route, legal/privacy pages, and Person/Organization structured data.
- **Product-led brand:** keep the site company-neutral, but standardize the
  developer name and avoid implying a corporate structure that is not
  documented.

Do not add “CEO” merely for prestige. “Founder and creator of Nomad Agent” is
supported today.

## 2. Portfolio snapshot

### Creator-level public footprint

The [Apify creator profile](https://apify.com/nomad-agent) snapshot retrieved
for this report shows:

| Metric | Public snapshot |
| --- | ---: |
| Public Actors | 57 |
| Total users | 405 |
| Monthly users | 198 |
| Runs succeeded | 92.9% |
| Issues response | 7.5 days |

These are portfolio metrics, not proof of the two normalized Actors’ health,
revenue, or customer satisfaction. They nevertheless show that the creator has
real distribution across a broad Actor catalog.

### Products in this repository

| Product | Intended buyer/use | Strongest value | Current boundary |
| --- | --- | --- | --- |
| LinkedIn normalized Actor | Job-alert products, job boards, recruiting/data workflows, agents | Source-linked normalized records, strict filters, recurring-delivery dedupe, optional company facts, enrichment, and translation | Local integrations target `1.0.2`; live exact-build proof was not refreshed |
| EURAXESS normalized Actor | Researcher alerts, academic platforms, research recruitment, labor-market feeds | Research taxonomy, funding, requirements, deadlines, contacts, multilingual search, dedupe, enrichment, and translation | Local integrations target `1.0.16`; live exact-build proof was not refreshed |
| Shared interoperability layer | Technical buyers using MCP, API, n8n, Make, Airtable, Sheets, or Agent Skills | One six-root `nomad-agent-job-v1` system of record plus a table-safe 32-field projection | Destination-specific writes require separate live validation |

Repository sources:

- [Product catalog and integration packs](../README.md)
- [Compatibility matrix](integration-compatibility.md)
- [Canonical and flat contracts](contracts.md)
- [LinkedIn Agent Skill](../.agents/skills/linkedin-enrich-translate-normalize-scraper/SKILL.md)
- [EURAXESS Agent Skill](../.agents/skills/euraxess-enrich-translate-normalize-scraper/SKILL.md)

### Adjacent portfolio signal

Public Apify snapshots suggest that simpler and bundled offers are currently
easier to adopt than the normalized specialist products:

| Adjacent Nomad Agent product | Public snapshot | Strategic signal |
| --- | --- | --- |
| LinkedIn Jobs Scraper — Short Output | 10 total users, 2 monthly active | A small, obvious payload may activate faster than a contract-heavy product |
| Researcher bundle | 16 total users, 3 monthly active | Multi-source academic outcomes appear more compelling than a single-source EURAXESS product |
| All Jobs bundle | 2 total users, 1 monthly active | Breadth alone is not sufficient; use-case clarity still matters |

These Store/search snapshots are cache-sensitive and directional. They should
be replaced by authenticated account analytics before making investment or
pricing decisions.

## 3. Product positioning

### Recommended category

**Open job-data infrastructure for recurring automations and AI agents.**

This is stronger than “another scraper.” It makes the shared contract,
source-specific evidence, duplicate-safe delivery, and maintained integration
assets commercially relevant.

### Internal positioning statement

For developers, recruiting/data teams, and job-product builders who need fresh
job records repeatedly, Nomad Agent is job-data infrastructure that turns
source-specific public listings into stable, source-linked, duplicate-safe
records. Unlike low-cost bulk scrapers or manual exports, it preserves evidence
semantics and ships maintained paths into agents, APIs, and automation tools.

### Three value pillars

1. **Trustworthy structure:** one canonical record, stable identity, explicit
   provenance, and no silent collapse of unknown versus empty values.
2. **Recurring delivery without duplicate noise:** job identity is
   `source:externalId`, with source-specific, tenant-scoped delivery controls.
3. **Ready for real workflows:** maintained MCP, REST, n8n, Make, Airtable,
   Sheets, and Agent Skill assets reduce integration work.

### Product-specific message

- **LinkedIn:** “Fresh LinkedIn jobs for alerts and data products, delivered as
  source-linked records without repeat noise.”
- **EURAXESS:** “Research and academic vacancies with funding, deadlines,
  requirements, contacts, and taxonomy preserved.”
- **Researcher bundle:** “One recurring academic/research feed across multiple
  boards.” This should be the primary top-of-funnel academic offer; normalized
  EURAXESS can remain the high-fidelity component/API.

## 4. Traction and distribution

### Normalized Actor public snapshots

| Product | List price shown | Total users | Monthly active | Bookmarks | Reviews |
| --- | ---: | ---: | ---: | ---: | ---: |
| [LinkedIn normalized Actor](https://apify.com/nomad-agent/linkedin-enrich-translate-normalize-scraper) | from $0.90 / 1,000 base results | 2 | 1 | 0 | 0 |
| [EURAXESS normalized Actor](https://apify.com/nomad-agent/euraxess-enrich-translate-normalize-scraper) | from $0.90 / 1,000 base results | 2 | 1 | 0 | 0 |

The pages were available through public web snapshots, while direct Actor API
and authenticated CLI reads timed out. Treat the numbers as dated/cached
public signals, not billing truth.

### Distribution assets already present

- public Store listings for both products;
- a dedicated static product/documentation site;
- direct, Actor-specific Apify CTAs in 12 placements;
- deterministic UTM parameters and local conversion events;
- Google and Bing verification tags;
- Agent Skills for LinkedIn and EURAXESS;
- MCP, REST, n8n, Make, Airtable, Google Sheets, and parser assets; and
- an open benchmark contract and human-review plan.

The local website contract suite confirms the CTA and attribution wiring, but
the site intentionally sends no analytics request unless a host installs
Plausible. Therefore the current report cannot answer:

- how many people visit the site;
- which Actor or placement earns clicks;
- how many clicks become first runs;
- how many first runs succeed;
- how many users return within 7 or 30 days; or
- which acquisition path generates paid usage.

The funnel is instrumentable but not measured.

## 5. Competitive landscape

### LinkedIn category

Public Apify snapshots retrieved for this report:

| Actor | From price / 1,000 | Total users | Monthly active | Reviews | Primary market advantage |
| --- | ---: | ---: | ---: | ---: | --- |
| Nomad Agent normalized | $0.90 | 2 | 1 | 0 | Contract fidelity, duplicate-safe delivery, integrations, optional managed enrichment |
| [Curious Coder](https://apify.com/curious_coder/linkedin-jobs-scraper) | $1.00 | 140K | 14K | Category leadership, full details, company/job-poster data, social proof |
| [Cheap Scraper](https://apify.com/cheap_scraper/linkedin-job-scraper) | $0.35 | 47K | 8.5K | Low tiered price, dedupe, 13 Tasks, tutorials, simple no-login story |
| [Valig](https://apify.com/valig/linkedin-jobs-scraper) | $0.28 | 21K | 5.3K | Very low price, high rating, simple job-search proposition |
| [Fantastic.jobs](https://apify.com/fantastic-jobs/advanced-linkedin-job-search-api) | $1.50 | 14K | 2.8K | Large indexed database, advanced filters, recruiter/company data, API upsell |

Nomad Agent is not overpriced relative to the leaders that sell richer data,
but it is materially more expensive than price-led competitors. Competing on
price would sacrifice the only defensible position. Compete on recurring
workflow quality, exact contracts, evidence, and integrations.

The market leaders also demonstrate the distribution gap: clear Tasks,
tutorials, reviews, examples, issue responsiveness, and a very simple first
promise. Those assets currently matter more than adding another output field.

### Academic/research category

| Actor | From price / 1,000 | Total users | Monthly active | Reviews | Position |
| --- | ---: | ---: | ---: | ---: | --- |
| Nomad Agent normalized EURAXESS | $0.90 | 2 | 1 | 0 | High-fidelity single-source normalized infrastructure |
| [Nomad Agent researcher bundle](https://apify.com/nomad-agent/researcher-bundle) | about $3.00 | 16 | 3 | 0 | Multi-source academic/research outcome |
| [ScholarStack EU academic aggregator](https://apify.com/scholarstack/eu-academic-research-jobs-aggregator) | $4.00 | 91 | 9 | 3 | Nine-source EU academic feed and weekly incremental use case |

The direct EURAXESS price is already low. Discounting is unlikely to solve the
category-size and use-case problem. The stronger route is to use EURAXESS as a
trusted source within a multi-source researcher workflow while keeping the
specialist Actor available to technical buyers who need its taxonomy and
evidence.

## 6. Pricing and unit-economics boundary

The public product pages currently show these event prices:

| Event | Customer list price per successful row | Creator gross at 80% before platform/provider costs |
| --- | ---: | ---: |
| Base job result | $0.0009 | $0.00072 |
| English translation | $0.006 | $0.0048 |
| Silver enrichment | $0.006 | $0.0048 |
| Gold enrichment | $0.010 | $0.0080 |

Apify’s publishing terms generally allocate 80% of event revenue to the
creator, with platform costs potentially deducted. At the base price, 1,000
results therefore represent $0.90 of customer revenue and at most $0.72 of
creator gross before costs.

LinkedIn `firstRunMode` is locally documented as a five-result preset that
forces Silver enrichment and supported-field translation. At the listed event
prices, the maximum charge is approximately **$0.0645** when all five rows
trigger all three events. The creator gross before costs would be at most
**$0.0516**. English rows or failed/unneeded optional work may cost less.

This report cannot calculate contribution margin because it lacks:

- actual per-Actor event volume and paid/free-plan mix;
- platform compute charges;
- LLM and translation provider costs;
- cache-hit rates by event;
- refunds, failed charges, or disputed runs; and
- support and maintenance time.

Do not make a discount decision before those values are reconciled.

Official policy source:
[Apify Store Publishing Terms](https://docs.apify.com/legal/store-publishing-terms-and-conditions).

## 7. Release and quality state

### Proof-layer ledger

| Layer | Status on 2026-08-27 | What it proves |
| --- | --- | --- |
| Checked-out committed baseline | `d016f7f`; LinkedIn `0.6.48`, EURAXESS `1.0.13` | What the current local `HEAD` contains |
| Current local integration work | 38 tracked files modified; assets now target LinkedIn `1.0.2` and EURAXESS `1.0.16`; benchmark and website assets are also untracked | A prepared local compatibility update, not publication |
| Offline repository suite | 117 tests passed | Local structural, contract, workflow, website, and secret-hygiene checks |
| Benchmark scorer | Self-test passed | The synthetic scorer/contract behaves locally; not real-world accuracy |
| Website JavaScript | `node --check` passed | Syntax only |
| Historical website evidence | Local evidence ledger records desktop/mobile QA, 12 attributed CTAs, 115 tests, and successful Actor-page probes on 2026-08-24 | Historical local/live website acceptance, not current Actor health |
| Public Store pages | Both product pages were discoverable through web snapshots | Public presence and displayed copy/pricing/stats |
| Live immutable Actor build | **Not refreshed**; CLI/API requests timed out | No current exact-build claim is valid from this report |
| Recent natural Actor run | **Not checked** | No current run-health claim |
| n8n/Make/Airtable/Sheets write | **Not checked** | No live destination-delivery claim |
| Current production website parity | **Not refreshed** | No current byte-for-byte deployment claim |

### Material release inconsistencies

1. **Version layers:** local assets target `1.0.2` / `1.0.16`, but committed
   `HEAD` still targets `0.6.48` / `1.0.13`. The worktree is not release proof.
2. **LinkedIn result limit:** the local `1.0.2` skill advertises a 1,000-item
   Actor window, while the n8n Google Sheets workflow still rejects
   `maxItems > 200`. Decide whether this is an intentional safe template cap
   and document it explicitly, or update the workflow and its tests.
3. **README status drift:** the catalog says supported LinkedIn `1.0.2`, while
   the Project Status section still says LinkedIn `0.6`.
4. **Public benchmark claim:** the public benchmark says there is no official
   human-verified accuracy percentage. The public LinkedIn Store page currently
   describes internal positive-heavy results as 99.44% for Silver and 99.15%
   for Gold. The Store copy includes caveats, but this still creates a claims
   governance conflict.

### Quality evidence that is valid

The internal LinkedIn challenge evidence supports regression confidence on a
selected positive-heavy field set. It does not support “99% accurate” as a
general product claim. There is no equivalent human-grounded EURAXESS semantic
score and no human-grounded translation-quality percentage. The repository’s
[benchmark status report](../benchmarks/enrichment-quality-v1/RESULTS.md) and
[release checklist](../benchmarks/enrichment-quality-v1/RELEASE_CHECKLIST.md)
set the correct publication boundary.

## 8. Risk register

| Risk | Severity | Why it matters | Executive response |
| --- | --- | --- | --- |
| Exact deployed build not currently proven | Critical | Integrations may call an incompatible contract or stale build | Re-read live pricing/schema/build, then run bounded exact-build canaries before release claims |
| Accuracy claim conflicts with benchmark status | High | Trust, marketplace review, and customer expectations | Align Store copy to the public benchmark boundary or complete human review first |
| No measurable acquisition funnel | High | Cannot distinguish low traffic, weak click-through, failed activation, or poor retention | Install privacy-conscious analytics and reconcile UTMs to first and repeat Actor use |
| Two normalized Actors have no reviews | High | Competitors have strong social proof and tutorials | Recruit real design partners and ask only genuine users for honest reviews |
| Brand/leadership identity is inconsistent | Medium | Weakens trust and knowledge-graph clarity | Choose founder-led or product-led identity and standardize names/pages/schema |
| Documentation/template limit drift | Medium | Users may see contradictory maximums | Decide intended caps and test the customer-visible rule |
| No verified destination writes in this audit | Medium | Templates are not proof of customer outcomes | Run disposable destination canaries separately for priority integrations |
| Unit economics unavailable | Medium | Price and tier decisions are guesswork | Build per-Actor revenue, variable-cost, cache, and support reporting |
| Source terms/privacy obligations | Medium–High | Public availability does not automatically authorize every reuse | Keep responsible-use guidance visible and obtain legal review for high-risk use cases |
| Portfolio breadth can dilute focus | Medium | 57 Actors can fragment maintenance and marketing | Concentrate promotion on a small number of use-case bundles and supporting specialist sources |

## 9. Ordered executive plan

### P0 — establish one release truth

1. Read current live Actor details, input schemas, pricing events, default/latest
   build pointers, and availability for both normalized Actors.
2. Verify immutable LinkedIn `1.0.2` and EURAXESS `1.0.16` artifacts against
   the local integration contracts.
3. Run one bounded base canary per Actor; reconcile terminal status, exact
   build, `RUN-SUMMARY`, complete dataset count, row contract, and charge.
4. Resolve the 200-versus-1,000 LinkedIn template boundary and the stale README
   `0.6` status line.
5. Align Store accuracy language with the public benchmark status.
6. Only then review, commit, push, publish, and verify the exact repository
   artifact. These are separate, explicitly authorized actions.

### P1 — instrument and activate

1. Install a real privacy-conscious analytics receiver for the existing website
   events; preserve UTM parameters through the Store/Task journey where Apify
   permits it.
2. Define the activation funnel: landing visit → Actor click → first run →
   successful delivered row → second run within 7 days → paid repeat use.
3. Publish three bounded Tasks/demos:
   - remote/hybrid software jobs in a named market;
   - duplicate-safe daily job alert to one destination; and
   - PhD/postdoc research alert by country/discipline.
4. Create one 60-second demo, one outcome-led tutorial, and one transparent
   “why this instead of a cheap scraper?” comparison.
5. Recruit 5–10 real design partners from job-alert builders, recruiting/data
   teams, academic career services, or researcher communities. Capture
   activation friction and request honest reviews only after delivered value.

### P2 — clarify brand and economics

1. Choose founder-led or product-led identity and standardize NomadDev / Nomad
   Agent naming across Apify, GitHub, and the site.
2. If founder-led, publish a short evidence-backed founder page without
   inventing a CEO title.
3. Add appropriate Contact, Privacy, Terms, and Organization/Person structured
   data if the site is intended to operate as a commercial trust surface.
4. Build a monthly Actor scorecard: users, MAU, first-run success, repeat use,
   event revenue, platform/provider cost, gross contribution, support load,
   reviews, and source failure rate.
5. Review the portfolio quarterly and promote bundles that pull specialist
   Actors into clear user outcomes.

## 10. Proposed 30-day scorecard

| Metric | Current evidence | 30-day objective |
| --- | --- | --- |
| Exact-build release proof | Missing from this audit | One complete immutable-build receipt per normalized Actor and per promoted release |
| Local integration validation | 117 tests passed | Preserve green suite and add assertions for every resolved customer-visible limit |
| Live destination proof | None in this audit | Disposable live write for the top two promoted destinations, reported separately |
| Public accuracy claim | Conflicting Store/repository boundary | Zero unqualified accuracy percentages; one consistent benchmark statement everywhere |
| Website funnel | Events exist, collector absent | Analytics receiving 100% of defined first-party CTA events; establish baseline rather than inventing a conversion target |
| LinkedIn normalized users | 2 total / 1 monthly in public snapshot | 10 new genuine first-run users and at least 3 repeat users |
| EURAXESS normalized users | 2 total / 1 monthly in public snapshot | Validate whether specialist buyers exist; route general academic acquisition to the researcher bundle |
| Reviews | 0 on both normalized Actors | At least 2 honest reviews from users who completed a real workflow |
| Unit economics | Unknown | Per-Actor event revenue and variable-cost report with cache/provider/platform separation |
| Brand identity | Fragmented names; no formal CEO source | One chosen naming policy and an evidence-backed founder/product identity decision |

Targets are operating proposals, not forecasts. Replace them once a measured
funnel baseline exists.

## 11. Evidence limits

This report used read-only workspace inspection, local tests, public product
pages, public creator profiles, and public competitor pages. It did not start
an Actor, enable a schedule, write to a destination, deploy a site, commit or
push repository changes, access private analytics, inspect billing, bypass
LinkedIn access controls, or query a corporate registry.

Public Store metrics and prices can change and some search results are cached.
Authenticated Actor metadata and run history were attempted read-only but did
not return before timeout. Any launch, price, revenue, or live-health decision
must therefore begin with a fresh authenticated read.

## Source index

### Local repository

- [README](../README.md)
- [Integration compatibility](integration-compatibility.md)
- [Contracts](contracts.md)
- [Website](../website/index.html)
- [Website success criteria](../website/SUCCESS_CRITERIA.md)
- [Benchmark status](../benchmarks/enrichment-quality-v1/RESULTS.md)
- [Benchmark human-review plan](../benchmarks/enrichment-quality-v1/HUMAN_REVIEW_PLAN.md)

### Public first-party and marketplace pages

- [NomadDev creator profile](https://apify.com/nomad-agent)
- [Lex Sherman / Exdenta](https://github.com/Exdenta)
- [Nomad Agent LinkedIn normalized Actor](https://apify.com/nomad-agent/linkedin-enrich-translate-normalize-scraper)
- [Nomad Agent EURAXESS normalized Actor](https://apify.com/nomad-agent/euraxess-enrich-translate-normalize-scraper)
- [Nomad Agent researcher bundle](https://apify.com/nomad-agent/researcher-bundle)
- [Nomad Agent website](https://nomadagent.dev/)
- [Apify Store Publishing Terms](https://docs.apify.com/legal/store-publishing-terms-and-conditions)
