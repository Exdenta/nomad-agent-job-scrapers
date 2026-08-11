#!/usr/bin/env python3
"""Repository entry point for the vendored fleet-v2 semantic validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path


IMPLEMENTATION = (
    Path(__file__).resolve().parents[2]
    / ".agents"
    / "skills"
    / "euraxess-enrich-translate-normalize-scraper"
    / "scripts"
    / "validate_run_summary.py"
)
SPEC = importlib.util.spec_from_file_location(
    "nomad_agent_fleet_run_summary_validator",
    IMPLEMENTATION,
)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"cannot load fleet run-summary validator: {IMPLEMENTATION}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

FleetRunSummaryValidationError = MODULE.FleetRunSummaryValidationError
validate_fleet_run_summary = MODULE.validate_fleet_run_summary
main = MODULE.main


if __name__ == "__main__":
    raise SystemExit(main())
