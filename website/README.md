# Nomad Agent website

Static marketing site for the Nomad Agent job-data platform. It has no runtime
dependencies, API keys, Firebase configuration, or analytics network request by
default.

## Local preview

From the repository root:

```bash
python3 -m http.server 4173 --directory website
```

Open `http://127.0.0.1:4173`.

## Conversion events

Every Apify CTA carries deterministic Actor and placement metadata plus UTM
attribution. Clicks dispatch a local `nomad-agent:analytics` `CustomEvent` whose
`detail` contains `event`, `actor`, and `placement`.

The site also forwards those events to `window.plausible` when a host installs
Plausible. Without that optional host integration, nothing is transmitted. The
same local hook reports Agent Skill selection and successful command copies.

## Verification

The acceptance gates are documented in `SUCCESS_CRITERIA.md`. Run the website
contract checks from the repository root with:

```bash
python3 -m unittest tests.test_website -v
```

## Firebase deployment

The repository is configured for the isolated `nomad-agent-job-scrapers`
Hosting site in the `hryu-jobs` Firebase project. The explicit site binding in
the root `firebase.json` prevents this deployment from replacing the project's
default Hosting site.

Deploy from the repository root:

```bash
firebase deploy --only hosting --project hryu-jobs
```

The public URL is `https://nomad-agent-job-scrapers.web.app`. No Firebase
application keys or environment variables are required for this static site.

## Automated production deployment and search discovery

`.github/workflows/deploy-website.yml` deploys the isolated Hosting site when
website or deployment files change on `main`. After Firebase reports success,
the workflow verifies the public canonical URLs and search artifacts before it:

1. submits `https://nomadagent.dev/sitemap.xml` through the Google Search
   Console API; and
2. sends every canonical URL in the sitemap to IndexNow, which includes Bing.

This is discovery notification, not guaranteed indexing or ranking. Google's
general Indexing API is deliberately not used because it is limited to pages
containing `JobPosting` or qualifying livestream structured data.

The workflow discovers deployable pages from `<link rel="canonical">` in each
HTML document. Fragment links such as `#actors` are sections of the home page,
not separate pages. Every new HTML page must therefore have one unique,
absolute `https://nomadagent.dev/...` canonical URL.

### One-time GitHub and console setup

Configure the `INDEXNOW_KEY` GitHub Actions secret before enabling the workflow.
It must be a random 8-128 character value containing only letters, numbers, and
dashes. The workflow publishes it only as `/indexnow-key.txt`, which is excluded
from Git.

Firebase and Search Console authenticate without a stored Google private key.
GitHub's OIDC token is exchanged through this Workload Identity Federation
provider:

```text
projects/783418209706/locations/global/workloadIdentityPools/github-actions/providers/nomad-agent-job-scrapers
```

The provider accepts only the `Exdenta/nomad-agent-job-scrapers` repository on
`refs/heads/main`. Its repository-scoped principal has Workload Identity User
on `github-nomad-agent-web@hryu-jobs.iam.gserviceaccount.com`. That service
account retains the narrow Firebase Hosting Admin and API Keys Viewer roles.

Enable the Search Console API for project `hryu-jobs`, then add the service
account email as a full user of the exact Search Console URL-prefix property
`https://nomadagent.dev/`. The workflow requests the `webmasters` OAuth scope
through Application Default Credentials created by
`google-github-actions/auth`.

Generate an IndexNow key locally with, for example:

```bash
openssl rand -hex 16
```

The workflow can also be run manually from GitHub Actions. Its post-deploy step
checks exact Search Console property access before deployment, then fails if the
live sitemap, canonical page, or IndexNow key file is not publicly available.
It reports Google and IndexNow submission failures separately.

For a read-only Google index snapshot after deployment, run
`python3 scripts/search_publish.py inspect` with Application Default
Credentials. It reports the indexed version's verdict, coverage, crawl, robots,
fetch, and canonical fields for every sitemap URL; it does not request
indexing. Bing's corresponding evidence is available in Webmaster Tools URL
Inspection and Site Explorer rather than from the IndexNow acceptance response.
