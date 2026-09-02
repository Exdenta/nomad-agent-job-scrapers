# Nomad Agent Job Scrapers

Open schemas, integration recipes, and agent skills for Nomad Agent job-search
Actors. The Actor implementations may be hosted services; this repository
publishes their interoperability layer, not a claim that every scraper is open
source.

## LinkedIn Jobs Scraper | Remove Duplicates | AI Enrichment

Find fresh public LinkedIn jobs, keep recurring alerts and trackers free of
duplicate deliveries, and send clean source-linked records into Google Sheets,
Slack, Telegram, email, Airtable, Make, n8n, MCP clients, or your own API.
Start with enrichment and translation off; enable either only when the extra
structured fields or English display values are useful to the workflow.

- [Build a daily new-job alert](integrations/n8n/linkedin-daily-job-alerts.json)
- [Build a duplicate-safe Google Sheets job tracker](integrations/n8n/linkedin-jobs-to-google-sheets.json)
- [Connect an agent that can find and monitor jobs](docs/agent-skills.md#one-command-linkedin-setup)

The LinkedIn and EURAXESS Actors turn public job postings into the same stable,
source-linked record shape. Both support precise filters, scheduled-alert
deduplication, optional description-backed enrichment, and selected-field
English translation without requiring customer model or translation keys.

> **Unofficial integrations.** This project and its Actors are independently
> developed. They are not affiliated with or endorsed by LinkedIn, EURAXESS,
> the European Commission, or source-site operators. Public page access is not
> authorization to crawl or republish personal data; review source terms,
> licensing, privacy obligations, and applicable law before use.

## Actor catalog

| Actor | Best for | Key advantages | Availability boundary |
| --- | --- | --- | --- |
| [`LinkedIn Jobs Scraper \| Remove Duplicates \| AI Enrichment`](https://apify.com/nomad-agent/linkedin-enrich-translate-normalize-scraper) | Public LinkedIn job search | Find fresh jobs, suppress already-delivered matches, and send clean records with complete descriptions when available to alerts, trackers, job boards, or agents. Optional enrichment and translation stay off until selected. | Public Store Actor; exact supported build `1.0.2` |
| [`EURAXESS Jobs Scraper — Research & Academic Jobs`](https://apify.com/nomad-agent/euraxess-enrich-translate-normalize-scraper) | PhD, postdoc, fellowship, research, and faculty vacancies | Research domains, requirements, funding, deadlines, contacts, multilingual keyword expansion, strict filters, deduplication, optional enrichment, and translation | Public Store Actor; exact supported build `1.0.16` |

Both target the six-root `nomad-agent-job-v1` envelope, but source-specific
inputs, evidence, custom fields, deployment state, and
pricing must not be assumed interchangeable. See the
[EURAXESS contract guide](docs/euraxess.md) and the
[integration compatibility matrix](docs/integration-compatibility.md) for the
exact boundaries.

## Public enrichment-quality benchmark

The [open benchmark contract and scorer](benchmarks/enrichment-quality-v1/README.md)
measure exact final-record enrichment, unsupported fills, deterministic-field
preservation, provenance integrity, repeated-run completion, and selected-field
translation for LinkedIn and EURAXESS separately. The first human-verified
dataset is still being prepared, so the repository does not yet publish an
official accuracy percentage. The current evidence and its limitations are
documented in the [benchmark status report](benchmarks/enrichment-quality-v1/RESULTS.md).
The [human review plan](benchmarks/enrichment-quality-v1/HUMAN_REVIEW_PLAN.md)
defines qualified reviewer recruitment, blind double-labeling, adjudication,
service options, and the bounded first GT pilot.

## Start with MCP

Connect only the tools needed by the current task. Both profiles use generic
`call-actor` so the exact build and cost caps are explicit:

```text
https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

Inspect Actor details, then use generic `call-actor` with build `1.0.2` for
LinkedIn or `1.0.16` for EURAXESS. Confirm terminal success, verify the exact
build through the Apify run API, validate minimal v4 `RUN-SUMMARY`, and
reconcile the default dataset.

Or let the Apify CLI configure a supported client:

```bash
apify login
apify mcp install codex --tools fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record
```

Replace `codex` with `claude-code` or `cursor` as needed. Then try:

```text
Search for up to 20 remote or hybrid TypeScript developer jobs in Spain,
posted within the last 7 days. Do not translate or use AI enrichment. Return a
compact table and keep the canonical normalized records available.
```

See [the complete MCP setup](docs/mcp.md) for ChatGPT, Claude, Cursor, and
Codex instructions and per-Actor compatibility gates.

## Integration packs

| Priority | Pack | Workflow | Status |
| --- | --- | --- | --- |
| 1 | [n8n](integrations/n8n/README.md) | Daily new-job alerts or a duplicate-safe Google Sheets tracker | Exact LinkedIn `1.0.2` and EURAXESS `1.0.16` pins; all current input fields supported |
| 2 | [Make](integrations/make/README.md) | Completed Actor run -> flatten -> Google Sheets upsert | Task-owned complete inputs; exact LinkedIn `1.0.2` and EURAXESS `1.0.16` pins required |
| 3 | [Airtable](integrations/airtable/README.md) | Import 32 fields and upsert on stable `jobKey` | Shared flat destination preset with `linkedin` and `euraxess` source choices |
| 4 | [MCP](integrations/mcp/README.md) | ChatGPT, Claude, Cursor, Codex, or another MCP client | Exact-build generic calls, terminal-status checks, and validated datasets for both |
| 5 | [API/webhook](integrations/api/README.md) | Custom job board, database, or internal application | Exact-build, bounded REST and idempotent webhook recipes for both Actors |
| 6 | [Python parsers](.agents/skills) | Validate canonical JSON or create the shared flat projection | Source-specific validators and dependency-free parsers for both Actors |

## Output policy

The Actor's canonical output remains the nested six-root
`nomad-agent-job-v1` record:

```text
schemaVersion, identity, data, custom, llm, raw
```

Integrations use a derived `nomad-agent-flat-job-v1` projection. The flat view
is convenient for tables and no-code tools, but it does not replace the
canonical record. In particular:

- deduplicate on `jobKey` (`source:externalId`), not job title;
- preserve the original record when downstream logic needs full requirements,
  contacts, provenance, or the distinction between `null` and `[]`;
- never infer missing values from prose unless the Actor's opt-in enrichment
  explicitly filled them;
- treat `raw: null` as valid when `includeRaw` is false.

## Agent skills

Repository-scoped Codex skills live under `.agents/skills` for both normalized
Actors. Claude Code users can install either into `.claude/skills`:

Set up the LinkedIn skill and the five scoped Apify MCP tools together in the
target project:

```bash
python3 scripts/setup_linkedin_monitor.py --client codex --target /path/to/your/project
```

Use `--client claude` or `--client both` when needed. Repeating the same command
keeps identical skill and MCP entries unchanged. The setup uses the dedicated
names `apify_linkedin_jobs` for Codex and `apify-linkedin-jobs` for Claude; it
preserves unrelated entries and fails closed if either dedicated name already
has different settings. It never embeds a token. Complete OAuth after setup
only after opening and trusting the target project in Codex; then run `codex
mcp login apify_linkedin_jobs`. For Claude Code, use its `/mcp` menu. Restart an
already-open client after trust and authentication. A locally modified skill is
never overwritten unless `--force-skill` is explicit.

For skill-only installation:

```bash
python3 scripts/install_skill.py --skill linkedin-enrich-translate-normalize-scraper \
  --client claude --target /path/to/your/project
python3 scripts/install_skill.py --skill euraxess-enrich-translate-normalize-scraper \
  --client claude --target /path/to/your/project
```

See [Agent skill setup](docs/agent-skills.md).

## Repository layout

```text
.agents/skills/   Codex-compatible Agent Skills
benchmarks/       Public quality contracts, scorers, fixtures, and results
docs/             MCP, contracts, and integration guidance
integrations/     Importable integration assets and shared projections
scripts/          Repository setup utilities
tests/            Offline contract and mapper tests
```

## Security and responsible use

- Prefer OAuth for the hosted Apify MCP server. Never commit an Apify token.
- Use the least-privilege MCP URL above instead of exposing every Actor/tool.
- Review the selected source's terms, licensing, privacy requirements, and
  applicable law for your use case.
- Do not publish personal data or raw descriptions to destination systems
  without confirming the destination's retention and access controls.

## Project status

LinkedIn `0.6` and EURAXESS `1.0` are public Store Actors. Pin the supported
exact build in every integration and verify destination behavior independently
before enabling a recurring workflow.

## License

The schemas, scripts, Agent Skills, examples, and documentation contained in
this repository are available under the [MIT License](LICENSE), including for
commercial use.

The license applies only to files published in this repository. Hosted Apify
Actor implementations are not included here and are not licensed by this
repository.
