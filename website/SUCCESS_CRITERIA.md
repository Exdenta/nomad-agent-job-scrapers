# Website success criteria

The expanded site is complete only when every applicable gate below has current
evidence. Local tests, a deployment, a search notification, and an indexed page
are separate proof layers.

## 1. Product and intent coverage

- The homepage presents three honest paths: collect job data, automate delivery,
  and score fit with evidence.
- LinkedIn, EURAXESS, and AI Job Fit Scorer each have a canonical product page
  with a bounded use case, input, output, limitation, version boundary, and
  direct Store CTA.
- Actor, integration, guide, and trust hubs make every intended page reachable
  through ordinary HTML links.
- Each task-led guide owns one distinct intent from `docs/seo-program.md`; the
  site does not manufacture thin role/location pages without maintained data.

## 2. Claim and contract accuracy

- Current Store defaults are labeled separately from older integration-tested
  pins: LinkedIn `1.0.6` versus `1.0.2`, EURAXESS `1.0.20` versus `1.0.16`, and
  scorer `0.1.11` for both, as observed on 2026-09-03.
- The scorer price is stated only as `$0.02 per successful retained evaluation`;
  no unsupported accuracy, customer, adoption, savings, or speed claim appears.
- `nomad-agent-job-v1`, `null` versus `[]`, exact-build, `RUN-SUMMARY`, partial
  failure, dataset reconciliation, and named-destination boundaries remain
  explicit.
- n8n/Make artifacts are never described as publicly listed, hosted-import
  tested, or destination-verified unless the corresponding evidence changes.
- The project states its non-affiliation with LinkedIn, EURAXESS, and job
  sources where relevant.

## 3. Search integrity and structured data

- Every indexable HTML document has one unique on-origin HTTPS canonical, title,
  description, H1, Open Graph set, Twitter card, and 1200×630 social image.
- Homepage JSON-LD describes Organization, WebSite, and the three-product
  ItemList; supporting pages use truthful breadcrumbs or page entities. No
  fabricated offers, ratings, reviews, or JobPosting inventory appears.
- `404.html` is useful, has `noindex,follow`, and declares no canonical.
- `sitemap.xml` contains exactly the indexable canonicals and `robots.txt`
  references it.
- Each public contract URL serves the exact checked-in schema with the matching
  `$id` and a JSON content type.

## 4. Conversion and privacy boundaries

- External Actor CTAs go directly to the correct Store Actor and include unique
  placement plus source, medium, campaign, and content attribution.
- Every measured action uses a stable `data-event` and bounded semantic fields.
- The default runtime creates no cookies, identifiers, query capture, or network
  analytics request; GPC/DNT suppresses event dispatch.
- A local browser event or attached analytics collector is not product
  activation, a successful Actor run, or a verified destination write.
- Support and design-partner paths warn users not to post resumes, secrets, or
  personal data in public issues.

## 5. Accessibility, function, and efficiency

- Semantic landmarks, a skip link, one H1, useful accessible names,
  keyboard-visible focus, and reduced-motion handling are present.
- Desktop and 390 px layouts have no horizontal overflow; the mobile menu,
  Escape close, Actor selector, and copy feedback work with keyboard input.
- All local routes, fragments, styles, scripts, icons, and images return HTTP
  200 from the documented preview server; a clean page load has no console
  errors.
- The site has no runtime package, hosted font, or required third-party request.
  Each HTML page plus shared CSS/JS/mark remains within the enforced test budget.
- The Firebase target is explicit, has no Functions or rewrites, and sends the
  repository security headers.

## 6. Verification and release gate

- Focused website, search-publication, measurement, and integration-copy tests
  pass, followed by the full repository suite.
- Generated artifacts are clean after `scripts/search_publish.py prepare`.
- Desktop and mobile browser QA covers representative hub, product, integration,
  guide, contract, trust, and 404 pages.
- A current deployment is matched to an exact commit, and live HTML/schema byte
  parity passes before any search notification.
- URL Inspection/index monitoring happens after deployment without treating
  notification acceptance as indexing.

## Evidence ledger

| Layer | Current status | Required or retained evidence |
| --- | --- | --- |
| Expanded 23-page implementation | Repository implementation recorded 2026-09-03; validation is attached to the exact commit | Checked-in pages, contracts, tests, browser QA, and the successful pull-request workflow for that commit |
| Production deployment | Established only by the exact successful `main` Firebase workflow receipt | Exact commit, successful Firebase workflow run, live byte parity |
| Google/IndexNow notification | Established only by the post-parity `main` workflow receipts | Post-parity workflow receipts; acceptance is never labeled indexing |
| Crawling and indexing | Monitored separately | URL Inspection and Bing state at 72-hour, 7-, 14-, 28-, 56-, and 84-day checkpoints |
| Search demand | Awaiting first complete 28-day baseline | Privacy-minimized weekly Search Console artifact; no invented target |
| Product outcomes/case studies | Not claimed | Consent, exact versions, reproducible metric, destination evidence, approved wording |
