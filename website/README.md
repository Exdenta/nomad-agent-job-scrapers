# Nomad Agent website

Static, dependency-free site for the Nomad Agent job-data catalog. The public
origin is `https://nomadagent.dev/`; Firebase Hosting serves the files in this
directory from the isolated `nomad-agent-job-scrapers` site in project
`hryu-jobs`.

## Information architecture

The site has three product pages, seven integration pages, four task-led guides,
and About, methodology, privacy, changelog, and contract pages. Every indexable
HTML file declares one absolute canonical. `404.html` is intentionally
`noindex,follow` and has no canonical.

The JSON schemas in `contracts/` must remain byte-for-byte copies of the
canonical sources in `integrations/shared/`. `scripts/search_publish.py prepare`
syncs the copies and regenerates `sitemap.xml` and `robots.txt`.

## Local preview and verification

From the repository root:

```bash
python3 scripts/search_publish.py prepare
python3 -m unittest tests.test_website tests.test_search_publish -v
python3 -m http.server 4173 --directory website
```

Open `http://127.0.0.1:4173/`. The complete acceptance contract and current
proof state are in `SUCCESS_CRITERIA.md`.

## Privacy-minimized interaction events

`script.js` dispatches a local `nomad-agent:analytics` `CustomEvent` for page
views and annotated actions. Its allowlist accepts only short semantic values
such as event, product, placement, destination, and format; it does not collect
cookies, user IDs, query strings, form content, or resume data. Global Privacy
Control or Do Not Track suppresses the events.

No event leaves the browser by default. A site owner may deliberately attach a
subscriber, an existing `dataLayer`, or Plausible. Such a collector is a
separate deployment and consent decision; the current static site does not
prove that any event was received or tied to a product outcome.

## Production deployment and search discovery

`.github/workflows/deploy-website.yml` runs on relevant changes to `main`. It:

1. validates the IndexNow secret and prepares generated artifacts;
2. rejects uncommitted sitemap, robots, or contract drift;
3. runs the full repository test suite;
4. uses GitHub OIDC for Google authentication and checks exact Search Console
   property access;
5. deploys the isolated Firebase Hosting target;
6. verifies every live HTML and schema response against the checked-out bytes;
7. only then submits the sitemap to Google and canonical URLs to IndexNow.

A deployment receipt proves deployment. Search Console or IndexNow acceptance
proves notification, not crawling, indexing, ranking, or traffic.

The workflow requires the repository-scoped Workload Identity provider and
service account already documented in `.github/workflows/deploy-website.yml`,
plus an `INDEXNOW_KEY` secret containing 8–128 letters, digits, or dashes. The
provider is restricted to `Exdenta/nomad-agent-job-scrapers` on
`refs/heads/main`, and the service account must be a full user of the exact
URL-prefix Search Console property `https://nomadagent.dev/`.

## Search measurement

`.github/workflows/seo-observatory.yml` captures a weekly 28-day Search Console
snapshot with raw query strings omitted, plus a read-only URL Inspection state
for every current canonical. The artifact is retained for 90 days. Search
Console reports top rows rather than a guaranteed exhaustive dataset, so the
report records that limitation. The operating cadence and evidence gates are in
`../docs/seo-program.md`.
