#!/usr/bin/env python3
"""Install one of this repository's job-Actor Agent Skills."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path


SKILL_NAME = "linkedin-enrich-translate-normalize-scraper"
SKILL_NAMES = (
    SKILL_NAME,
    "euraxess-enrich-translate-normalize-scraper",
    "ai-job-fit-scorer",
    "ycombinator-enrich-translate-normalize-scraper",
)


class UnsafeDestinationError(ValueError):
    """Raised when an install path can escape the selected project."""


@dataclass(frozen=True)
class InstallPlan:
    client: str
    destination: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill",
        choices=SKILL_NAMES,
        default=SKILL_NAME,
        help="Skill to install (default: LinkedIn)",
    )
    parser.add_argument("--client", choices=("codex", "claude", "both"), required=True)
    parser.add_argument("--target", type=Path, required=True, help="Target project directory")
    parser.add_argument("--force", action="store_true", help="Replace an existing installed copy")
    return parser.parse_args()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_destination(target: Path, destination: Path, *, force: bool) -> None:
    """Resolve and validate the full parent chain without mutating it."""
    if not _is_within(destination, target):
        raise UnsafeDestinationError(f"destination escapes target: {destination}")

    resolved_parent = destination.parent.resolve(strict=False)
    if not _is_within(resolved_parent, target):
        raise UnsafeDestinationError(
            f"destination parent resolves outside target: {destination.parent}"
        )

    relative_parent = destination.parent.relative_to(target)
    current = target
    for component in relative_parent.parts:
        current = current / component
        if current.is_symlink():
            raise UnsafeDestinationError(
                f"destination parent must not traverse a symlink: {current}"
            )
        if current.exists() and not current.is_dir():
            raise NotADirectoryError(f"destination parent is not a directory: {current}")

    if destination.is_symlink():
        raise UnsafeDestinationError(f"destination must not be a symlink: {destination}")
    if destination.exists() and not destination.is_dir():
        raise NotADirectoryError(f"destination is not a directory: {destination}")
    if destination.exists() and not force:
        raise FileExistsError(
            f"destination exists: {destination}; pass --force to replace it"
        )


def _missing_parents(target: Path, parent: Path) -> list[Path]:
    missing: list[Path] = []
    current = parent
    while current != target:
        if not current.exists():
            missing.append(current)
        current = current.parent
    return missing


def _stage(source: Path, staging_root: Path, plans: list[InstallPlan]) -> dict[Path, Path]:
    staged: dict[Path, Path] = {}
    for index, plan in enumerate(plans):
        staged_path = staging_root / f"{index}-{plan.client}"
        shutil.copytree(
            source,
            staged_path,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        staged[plan.destination] = staged_path
    return staged


def _commit(
    target: Path,
    plans: list[InstallPlan],
    staged: dict[Path, Path],
    *,
    skill_name: str = SKILL_NAME,
) -> None:
    installed: list[Path] = []
    backups: list[tuple[Path, Path]] = []
    created_parents: set[Path] = set()
    try:
        for plan in plans:
            destination = plan.destination
            missing = _missing_parents(target, destination.parent)
            destination.parent.mkdir(parents=True, exist_ok=True)
            created_parents.update(missing)
            _validate_destination(target, destination, force=True)

            if destination.exists():
                backup = destination.parent / (
                    f".{skill_name}.backup-{uuid.uuid4().hex}"
                )
                destination.rename(backup)
                backups.append((destination, backup))

            staged[destination].rename(destination)
            installed.append(destination)
    except BaseException:
        for destination in reversed(installed):
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
        for destination, backup in reversed(backups):
            if backup.exists():
                backup.rename(destination)
        for parent in sorted(created_parents, key=lambda item: len(item.parts), reverse=True):
            try:
                parent.rmdir()
            except OSError:
                pass
        raise

    for _destination, backup in backups:
        try:
            shutil.rmtree(backup)
        except OSError as exc:
            print(f"warning: could not remove backup {backup}: {exc}", file=sys.stderr)


def install_all(
    source: Path,
    target: Path,
    plans: list[InstallPlan],
    *,
    force: bool,
    skill_name: str = SKILL_NAME,
) -> None:
    """Preflight every client, stage every copy, then commit with rollback."""
    for plan in plans:
        _validate_destination(target, plan.destination, force=force)

    with tempfile.TemporaryDirectory(prefix=".nomad-skill-stage-", dir=target) as directory:
        staged = _stage(source, Path(directory), plans)
        _commit(target, plans, staged, skill_name=skill_name)

    for plan in plans:
        print(f"installed {skill_name} -> {plan.destination}")


def main() -> int:
    args = parse_args()
    repository = Path(__file__).resolve().parents[1]
    skill_name = args.skill
    source = repository / ".agents" / "skills" / skill_name
    if not source.is_dir():
        raise FileNotFoundError(f"source skill not found: {source}")

    target = args.target.expanduser().resolve(strict=True)
    if not target.is_dir():
        raise NotADirectoryError(f"target project does not exist: {target}")

    plans: list[InstallPlan] = []
    if args.client in {"codex", "both"}:
        plans.append(
            InstallPlan(
                client="codex",
                destination=target / ".agents" / "skills" / skill_name,
            )
        )
    if args.client in {"claude", "both"}:
        plans.append(
            InstallPlan(
                client="claude",
                destination=target / ".claude" / "skills" / skill_name,
            )
        )

    install_all(source, target, plans, force=args.force, skill_name=skill_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
