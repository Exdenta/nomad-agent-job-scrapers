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

The EURAXESS skill documents the public `1.0` contract on exact build `1.0.13`.
Its client setup uses generic `call-actor` to pin and verify that build rather
than rely on mutable `latest` or `canary` tags. It then validates minimal v4
`RUN-SUMMARY`, reconciles `delivered` with the dataset, and honors at most one
bounded retry recommendation. Installing it is not evidence that the Actor is
currently available, priced for a specific account, or authorized for the
current account.

The installed skill also contains `references/client-setup.md`, so an agent can
explain the Codex or Claude Code connection boundary without copying an Apify
token into a prompt or repository.
