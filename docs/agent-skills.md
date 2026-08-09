# Agent skill setup

The LinkedIn skill teaches an agent how to build safe Actor inputs, retrieve
complete MCP output, validate the normalized envelope, and create a derived
flat integration view.

## Codex

Codex discovers repository skills under `.agents/skills`. If this repository is
your working directory, no installation is needed. Invoke the skill explicitly
with:

```text
$linkedin-enrich-translate-normalize-scraper
```

To install it into another project:

```bash
python3 scripts/install_skill.py --client codex --target /path/to/project
```

The installer writes to `/path/to/project/.agents/skills`.
Codex personal skills use `$HOME/.agents/skills`; copy the skill there only
when it should be available in every project.

## Claude Code

Install into another project:

```bash
python3 scripts/install_skill.py --client claude --target /path/to/project
```

The installer writes to `/path/to/project/.claude/skills`. Restart Claude Code
only if the top-level skills directory did not exist when the session started.
Invoke the installed skill with
`/linkedin-enrich-translate-normalize-scraper`.

## Both clients

```bash
python3 scripts/install_skill.py --client both --target /path/to/project
```

Use `--force` only when you intend to replace an existing installed copy. The
installer never copies secrets and the skill has no third-party Python
dependencies.

Installing the skill does not install MCP. Complete the client setup in
[MCP quickstart](mcp.md) as a separate step.

The installed skill also contains `references/client-setup.md`, so an agent can
explain the Codex or Claude Code connection boundary without copying an Apify
token into a prompt or repository.
