# Nomad Agent Job Scrapers

Open schemas, integration recipes, and agent skills for Nomad Agent job-search
Actors. The Actor implementations may be hosted services; this repository
publishes their interoperability layer, not a claim that every scraper is open
source.

> **Unofficial integrations.** This project and its Actors are independently
> developed. They are not affiliated with or endorsed by LinkedIn, EURAXESS,
> the European Commission, or source-site operators. Public page access is not
> authorization to crawl or republish personal data; review source terms,
> licensing, privacy obligations, and applicable law before use.

## Actor catalog

| Actor | Source focus | Contract represented here | Availability boundary |
| --- | --- | --- | --- |
| [`nomad-agent/linkedin-enrich-translate-normalize-scraper`](https://apify.com/nomad-agent/linkedin-enrich-translate-normalize-scraper) | LinkedIn jobs | Public Store Actor (`0.6.24`) | Store-listed normalized Actor; `latest` and `canary` point to the validated `0.6.24` build |
| `nomad-agent/euraxess-enrich-translate-normalize-scraper` | EURAXESS PhD, postdoc, fellowship, research, and faculty vacancies | Private `1.0` canary | Build `1.0.4` is private and CI-qualified; `latest` remains on legacy `0.5.1`, and live source/destination canaries are still blocked |

Both target the six-root `nomad-agent-job-v1` envelope, but source-specific
inputs, evidence, custom fields, run-summary versions, deployment state, and
pricing must not be assumed interchangeable. See the
[EURAXESS contract guide](docs/euraxess.md) for its exact boundary.

## Start with MCP

Connect only the Actor needed by the current task. LinkedIn candidate endpoint:

```text
https://mcp.apify.com?tools=nomad-agent/linkedin-enrich-translate-normalize-scraper
```

EURAXESS compatibility-inspection endpoint:

```text
https://mcp.apify.com?tools=fetch-actor-details,nomad-agent/euraxess-enrich-translate-normalize-scraper
```

Do not run the EURAXESS `latest` tag: it remains on legacy `0.5.1`. Inspect the
Actor details and pin private qualification to version `1.0` or the `canary`
tag, whose schema must advertise `nomad-agent-job-search-input-v1`.

Or let the Apify CLI configure a supported client:

```bash
apify login
apify mcp install codex --tools nomad-agent/linkedin-enrich-translate-normalize-scraper
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
| 1 | [n8n](integrations/n8n/README.md) | Schedule -> Actor -> flatten -> Google Sheets append-or-update | Separate LinkedIn and EURAXESS imports; LinkedIn live-validated, EURAXESS offline-validated for the private `1.0` contract |
| 2 | [Make](integrations/make/README.md) | Completed Actor run -> flatten -> Google Sheets upsert | Separate LinkedIn and EURAXESS blueprints; EURAXESS has no automatic paid retry |
| 3 | [Airtable](integrations/airtable/README.md) | Import 32 fields and upsert on stable `jobKey` | Shared flat destination preset with `linkedin` and `euraxess` source choices |
| 4 | [MCP](integrations/mcp/README.md) | ChatGPT, Claude, Cursor, Codex, or another MCP client | Scoped LinkedIn and EURAXESS configurations; deployed compatibility must be inspected before a paid run |
| 5 | API/webhook | Custom job board, database, or internal application | Planned |

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

The integration repository is under active development. LinkedIn `0.6` and
EURAXESS `1.0` are pre-release contracts here. EURAXESS private canary build
`1.0.4` now implements the documented rewrite, while `latest` deliberately
remains on `0.5.1`. Private canary and destination-platform evidence remains
documented per pack and is never proof
of Store publication, general production readiness, current source
authorization, or future source continuity.

## License

The schemas, scripts, Agent Skills, examples, and documentation contained in
this repository are available under the [MIT License](LICENSE), including for
commercial use.

The license applies only to files published in this repository. Hosted Apify
Actor implementations are not included here and are not licensed by this
repository.
