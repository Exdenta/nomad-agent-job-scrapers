# Nomad Agent Job Scrapers

Open schemas, integration recipes, and agent skills for Nomad Agent job-search
Actors. The Actor implementations may be hosted services; this repository
publishes their interoperability layer, not a claim that every scraper is open
source.

The first supported source is the Apify Actor
[`nomad-agent/linkedin-enrich-translate-normalize-scraper`](https://apify.com/nomad-agent/linkedin-enrich-translate-normalize-scraper).

The LinkedIn Actor's `0.6` base path is deployed and has been live-validated
with bounded production runs. The reusable n8n template is also live-validated
through Google Sheets; destination-specific packs document the exact boundary
of their end-to-end validation.

## Start with MCP

Connect only this Actor to an MCP client:

```text
https://mcp.apify.com?tools=nomad-agent/linkedin-enrich-translate-normalize-scraper
```

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
Codex instructions.

## Integration packs

| Priority | Pack | Workflow | Status |
| --- | --- | --- | --- |
| 1 | [n8n](integrations/n8n/README.md) | Schedule -> Actor -> flatten -> Google Sheets append-or-update | Public import; Apify + n8n Cloud + Google Sheets live-validated |
| 2 | Make | Completed run -> dataset -> Sheets or Airtable -> Slack or email | Planned |
| 3 | Airtable | Field mapping and duplicate detection using stable job identity | Planned |
| 4 | MCP | ChatGPT, Claude, Cursor, Codex, or another MCP client | Initial implementation |
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

The repository-scoped Codex skill lives in
`.agents/skills/linkedin-enrich-translate-normalize-scraper`. Claude Code users
can install the same skill into `.claude/skills` with the included installer:

```bash
python3 scripts/install_skill.py --client claude --target /path/to/your/project
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
- Review LinkedIn's terms and applicable law for your use case.
- Do not publish personal data or raw descriptions to destination systems
  without confirming the destination's retention and access controls.

## Project status

The integration repository is under active development. The LinkedIn Actor
`0.6` base contract is live; MCP client-specific and destination-platform
validation remains documented per pack.

## License

The schemas, scripts, Agent Skills, examples, and documentation contained in
this repository are available under the [MIT License](LICENSE), including for
commercial use.

The license applies only to files published in this repository. Hosted Apify
Actor implementations are not included here and are not licensed by this
repository.
