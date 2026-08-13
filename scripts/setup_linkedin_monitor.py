#!/usr/bin/env python3
"""Install the LinkedIn skill and project-scoped Apify MCP configuration."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import tomllib


SKILL = "linkedin-enrich-translate-normalize-scraper"
MCP_URL = (
    "https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,"
    "get-dataset-items,get-key-value-store-record"
)
CODEX_SERVER = "apify_linkedin_jobs"
CLAUDE_SERVER = "apify-linkedin-jobs"
CLIENTS = ("codex", "claude", "both")
SKILL_DESTINATIONS = {
    "codex": Path(".agents") / "skills" / SKILL,
    "claude": Path(".claude") / "skills" / SKILL,
}
IGNORED_SKILL_NAMES = {".DS_Store"}
CODEX_ENTRY = {
    "url": MCP_URL,
    "auth": "oauth",
    "default_tools_approval_mode": "prompt",
    "tool_timeout_sec": 60,
}
CLAUDE_ENTRY = {
    "type": "http",
    "url": MCP_URL,
    "timeout": 600000,
}


@dataclass(frozen=True)
class ConfigUpdate:
    client: str
    path: Path
    content: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client",
        choices=CLIENTS,
        default="codex",
        help="Agent client to configure (default: codex)",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path.cwd(),
        help="Project that should receive the skill and MCP config (default: cwd)",
    )
    parser.add_argument(
        "--force-skill",
        action="store_true",
        help="Replace an existing project-scoped skill copy",
    )
    return parser.parse_args()


def _selected_clients(client: str) -> tuple[str, ...]:
    if client == "both":
        return ("codex", "claude")
    return (client,)


def _skill_manifest(root: Path) -> dict[str, tuple[str, str]]:
    """Return a content manifest compatible with install_skill.py exclusions."""
    manifest: dict[str, tuple[str, str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts:
            continue
        if path.name in IGNORED_SKILL_NAMES or path.suffix == ".pyc":
            continue
        key = relative.as_posix()
        if path.is_symlink():
            manifest[key] = ("symlink", str(path.readlink()))
        elif path.is_dir():
            manifest[key] = ("directory", "")
        elif path.is_file():
            manifest[key] = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
        else:
            manifest[key] = ("other", "")
    return manifest


def ensure_skill(
    repository: Path,
    target: Path,
    *,
    client: str,
    force_skill: bool,
) -> None:
    """Install missing skill copies; keep identical copies; reject modified copies."""
    source = repository / ".agents" / "skills" / SKILL
    source_manifest = _skill_manifest(source)
    pending: list[str] = []
    modified: list[Path] = []

    for skill_client in _selected_clients(client):
        destination = target / SKILL_DESTINATIONS[skill_client]
        if destination.is_dir() and not destination.is_symlink():
            if not force_skill and _skill_manifest(destination) == source_manifest:
                print(f"skill already current; keeping {destination}")
                continue
            if not force_skill:
                modified.append(destination)
                continue
        pending.append(skill_client)

    if modified:
        paths = ", ".join(str(path) for path in modified)
        raise FileExistsError(
            "installed skill differs from this repository; refusing to overwrite: "
            f"{paths}. Review it, then pass --force-skill to replace it."
        )
    if not pending:
        return

    install_client = "both" if pending == ["codex", "claude"] else pending[0]
    command = [
        sys.executable,
        str(repository / "scripts" / "install_skill.py"),
        "--skill",
        SKILL,
        "--client",
        install_client,
        "--target",
        str(target),
    ]
    if force_skill:
        command.append("--force")
    subprocess.run(command, check=True, cwd=repository)


def _validate_config_path(target: Path, path: Path) -> None:
    """Reject config paths that traverse symlinks or leave the selected target."""
    try:
        relative = path.relative_to(target)
    except ValueError as error:
        raise ValueError(f"config path escapes target: {path}") from error

    current = target
    for component in relative.parts[:-1]:
        current = current / component
        if current.is_symlink():
            raise ValueError(f"config parent must not be a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise NotADirectoryError(f"config parent is not a directory: {current}")
    if path.is_symlink():
        raise ValueError(f"config file must not be a symlink: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"config path is not a regular file: {path}")


def _same_remote_entry(entry: object, expected: dict[str, object]) -> bool:
    """Require whole-entry equality; hidden auth/tool settings are significant."""
    return isinstance(entry, dict) and entry == expected


def _plan_codex(target: Path) -> ConfigUpdate | None:
    path = target / ".codex" / "config.toml"
    _validate_config_path(target, path)
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    try:
        parsed = tomllib.loads(original)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"cannot safely merge invalid Codex config {path}: {error}") from error
    servers = parsed.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"Codex mcp_servers must be a table: {path}")
    if CODEX_SERVER in servers:
        if _same_remote_entry(servers[CODEX_SERVER], CODEX_ENTRY):
            print(f"Codex MCP config already current; keeping {path}")
            return None
        raise FileExistsError(
            f"Codex MCP server {CODEX_SERVER!r} already exists with a different "
            f"configuration in {path}; refusing to overwrite it"
        )

    prefix = original
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix:
        prefix += "\n"
    addition = (
        f"[mcp_servers.{CODEX_SERVER}]\n"
        f"url = {json.dumps(MCP_URL)}\n"
        'auth = "oauth"\n'
        'default_tools_approval_mode = "prompt"\n'
        "tool_timeout_sec = 60\n"
    )
    content = prefix + addition
    try:
        candidate = tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(
            f"cannot append a project MCP table without rewriting {path}: {error}"
        ) from error
    if not _same_remote_entry(candidate["mcp_servers"][CODEX_SERVER], CODEX_ENTRY):
        raise AssertionError("generated Codex MCP entry did not round-trip")
    return ConfigUpdate("Codex", path, content)


def _plan_claude(target: Path) -> ConfigUpdate | None:
    path = target / ".mcp.json"
    _validate_config_path(target, path)
    if path.exists():
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"cannot safely merge invalid Claude config {path}: {error}") from error
    else:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError(f"Claude MCP config must contain one JSON object: {path}")
    servers = parsed.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"Claude mcpServers must be an object: {path}")
    if CLAUDE_SERVER in servers:
        if _same_remote_entry(servers[CLAUDE_SERVER], CLAUDE_ENTRY):
            print(f"Claude MCP config already current; keeping {path}")
            return None
        raise FileExistsError(
            f"Claude MCP server {CLAUDE_SERVER!r} already exists with a different "
            f"configuration in {path}; refusing to overwrite it"
        )
    servers[CLAUDE_SERVER] = CLAUDE_ENTRY.copy()
    return ConfigUpdate("Claude", path, json.dumps(parsed, indent=2) + "\n")


def plan_mcp_configs(target: Path, client: str) -> list[ConfigUpdate]:
    """Preflight all selected configs before making any MCP change."""
    updates: list[ConfigUpdate] = []
    for selected in _selected_clients(client):
        update = _plan_codex(target) if selected == "codex" else _plan_claude(target)
        if update is not None:
            updates.append(update)
    return updates


def _atomic_write(update: ConfigUpdate) -> None:
    update.path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(update.path.stat().st_mode) if update.path.exists() else 0o644
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=update.path.parent,
            prefix=f".{update.path.name}.",
            delete=False,
        ) as handle:
            handle.write(update.content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        temporary.chmod(mode)
        os.replace(temporary, update.path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    print(f"configured {update.client} project MCP -> {update.path}")


def main() -> int:
    args = parse_args()
    repository = Path(__file__).resolve().parents[1]
    target = args.target.expanduser().resolve(strict=True)
    if not target.is_dir():
        raise NotADirectoryError(f"target project does not exist: {target}")

    # Preflight both selected MCP destinations before the skill or either config
    # is changed. A filesystem interruption can still leave a partial state;
    # identical-entry recognition makes the same command safe to resume.
    updates = plan_mcp_configs(target, args.client)
    ensure_skill(
        repository,
        target,
        client=args.client,
        force_skill=args.force_skill,
    )
    for update in updates:
        _atomic_write(update)

    print("LinkedIn job monitor setup complete.")
    if "codex" in _selected_clients(args.client):
        print("Open and trust the target project in Codex before MCP authentication.")
        print(f"Authenticate Codex once with: codex mcp login {CODEX_SERVER}")
    if "claude" in _selected_clients(args.client):
        print(f"In Claude Code, open /mcp and authenticate {CLAUDE_SERVER}.")
    print("Restart the selected agent client if it was already open.")
    print(
        "Then invoke $linkedin-enrich-translate-normalize-scraper and ask: "
        '"Find and monitor remote TypeScript jobs in Spain; keep AI enrichment '
        'and translation off."'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
