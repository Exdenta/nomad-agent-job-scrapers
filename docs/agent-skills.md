# Agent skill setup

The LinkedIn and EURAXESS skills teach an agent how to build source-accurate
Actor inputs, retrieve complete MCP output, validate the normalized envelope,
and create a derived flat integration view. Each skill includes its own
source-specific validator and availability boundary.

## Codex

Codex discovers repository skills under `.agents/skills`. If this repository is
your working directory, no installation is needed. Invoke the skill explicitly
with:

```text
$linkedin-enrich-translate-normalize-scraper
$euraxess-enrich-translate-normalize-scraper
```

To install it into another project:

```bash
python3 scripts/install_skill.py --skill linkedin-enrich-translate-normalize-scraper \
  --client codex --target /path/to/project
python3 scripts/install_skill.py --skill euraxess-enrich-translate-normalize-scraper \
  --client codex --target /path/to/project
```

The installer writes to `/path/to/project/.agents/skills`.
Codex personal skills use `$HOME/.agents/skills`; copy the skill there only
when it should be available in every project.

## Claude Code

Install into another project:

```bash
python3 scripts/install_skill.py --skill euraxess-enrich-translate-normalize-scraper \
  --client claude --target /path/to/project
```

The installer writes to `/path/to/project/.claude/skills`. Restart Claude Code
only if the top-level skills directory did not exist when the session started.
Invoke the installed skill with `/linkedin-enrich-translate-normalize-scraper`
or `/euraxess-enrich-translate-normalize-scraper`.

## Both clients

```bash
python3 scripts/install_skill.py --skill euraxess-enrich-translate-normalize-scraper \
  --client both --target /path/to/project
```

Use `--force` only when you intend to replace an existing installed copy. The
installer never copies secrets and the skill has no third-party Python
dependencies.

Installing the skill does not install MCP. Complete the client setup in
[MCP quickstart](mcp.md) as a separate step.

## One-command LinkedIn setup

From this repository, install the LinkedIn Agent Skill into a project and add
the scoped Apify MCP tools to Codex with one command:

```bash
python3 scripts/setup_linkedin_monitor.py --client codex --target /path/to/project
```

Use `--client claude` or `--client both` when needed. The command writes only
project-scoped, credential-free configuration under the dedicated names
`apify_linkedin_jobs` in `.codex/config.toml` and `apify-linkedin-jobs` in
`.mcp.json`. Existing unrelated servers, including a generic `apify` entry, are
preserved. An exact skill or MCP entry is a no-op; a modified skill or a
different entry under either dedicated name fails closed. `--force-skill`
applies only to the skill and never overwrites MCP configuration.

Codex loads a project `.codex/config.toml` only for a trusted project. Open and
trust the target project first, then complete OAuth:

```bash
codex mcp login apify_linkedin_jobs
```

For Claude Code, open `/mcp` and authenticate `apify-linkedin-jobs`. Restart an
already-open client only after trust and authentication. If a
filesystem interruption leaves only one client configured during `--client
both`, rerun the same setup command; the completed client is recognized and the
missing client is added without changing the first.

After setup, restart a client that was already open and invoke:

```text
$linkedin-enrich-translate-normalize-scraper
Find and monitor remote TypeScript jobs in Spain. Keep AI enrichment and
translation off, cap each search at 20 jobs, and use a stable dedupe scope for
future runs.
```

The skill pins and verifies LinkedIn build `1.0.2`; the MCP connection supplies
authentication and only the five tools needed for Actor details, execution,
run status, completion records, and dataset retrieval. Setup does not create an
Apify schedule by itself. Use the n8n daily-alert template or an Apify Task and
schedule when unattended monitoring is required.

The EURAXESS skill documents the public `1.0` contract on exact build `1.0.16`.
Its client setup uses generic `call-actor` to pin and verify that build rather
than rely on mutable `latest` or `canary` tags. It then validates minimal v4
`RUN-SUMMARY`, reconciles `delivered` with the dataset, and honors at most one
bounded retry recommendation. Installing it is not evidence that the Actor is
currently available, priced for a specific account, or authorized for the
current account.

The installed skill also contains `references/client-setup.md`, so an agent can
explain the Codex or Claude Code connection boundary without copying an Apify
token into a prompt or repository.

## Y Combinator normalized jobs

The [ycombinator-enrich-translate-normalize-scraper](../.agents/skills/ycombinator-enrich-translate-normalize-scraper/SKILL.md) skill covers startup-job search, recurring-alert dedupe, exact-build calls, and v4 completion checks.

```bash
python3 scripts/install_skill.py --skill ycombinator-enrich-translate-normalize-scraper --client both --target /path/to/project
```

See the [YC guide](ycombinator.md) for current prices and source limitations.
