#!/usr/bin/env python3
"""Install this repository's LinkedIn Agent Skill into another project."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SKILL_NAME = "linkedin-enrich-translate-normalize-scraper"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "claude", "both"), required=True)
    parser.add_argument("--target", type=Path, required=True, help="Target project directory")
    parser.add_argument("--force", action="store_true", help="Replace an existing installed copy")
    return parser.parse_args()


def install(source: Path, destination: Path, *, force: bool) -> None:
    if destination.exists() or destination.is_symlink():
        if not force:
            raise FileExistsError(f"destination exists: {destination}; pass --force to replace it")
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    print(f"installed {SKILL_NAME} -> {destination}")


def main() -> int:
    args = parse_args()
    repository = Path(__file__).resolve().parents[1]
    source = repository / ".agents" / "skills" / SKILL_NAME
    if not source.is_dir():
        raise FileNotFoundError(f"source skill not found: {source}")

    target = args.target.expanduser().resolve()
    if not target.is_dir():
        raise NotADirectoryError(f"target project does not exist: {target}")

    roots = []
    if args.client in {"codex", "both"}:
        roots.append(target / ".agents" / "skills")
    if args.client in {"claude", "both"}:
        roots.append(target / ".claude" / "skills")

    for root in roots:
        install(source, root / SKILL_NAME, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
