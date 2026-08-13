"""Factual run-status policy shared by LinkedIn and EURAXESS integrations.

Automatic paid retries are deliberately disabled. A caller may deliver only a
terminal successful Actor run whose fleet-v2 RUN-SUMMARY is valid and whose
status is ``succeeded`` or ``empty``. The summary reports facts; no field in it
authorizes another run.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from validate_fleet_run_summary import (
    FleetRunSummaryValidationError,
    validate_fleet_run_summary,
)


TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}


class RunStateError(ValueError):
    """Raised when run metadata cannot support a safe delivery decision."""


@dataclass(frozen=True, slots=True)
class RunDecision:
    fetch_dataset: bool
    automatic_retry: bool
    reason: str
    summary_status: str | None = None


def evaluate_terminal_run(run: Any, summary: Any = None) -> RunDecision:
    """Return the fail-closed dataset action for one Actor run.

    ``exitCode`` may be absent from some MCP projections; Apify's terminal
    ``SUCCEEDED`` state remains authoritative there. When it is present it must
    be exactly zero.
    """
    if not isinstance(run, dict):
        raise RunStateError("run metadata must be an object")
    status = run.get("status")
    if status not in TERMINAL_STATUSES:
        raise RunStateError(f"run is not terminal: {status!r}")
    exit_code = run.get("exitCode")
    if exit_code is not None and (
        isinstance(exit_code, bool) or not isinstance(exit_code, int)
    ):
        raise RunStateError("run exitCode must be an integer or null")
    if status != "SUCCEEDED" or exit_code not in {None, 0}:
        return RunDecision(False, False, status.lower())
    if summary is None:
        return RunDecision(False, False, "missing-run-summary")
    try:
        validated = validate_fleet_run_summary(summary)
    except FleetRunSummaryValidationError as exc:
        raise RunStateError(f"invalid RUN-SUMMARY: {exc}") from exc
    summary_status = str(validated["status"])
    if summary_status not in {"succeeded", "empty"}:
        return RunDecision(
            False,
            False,
            f"run-summary-{summary_status}",
            summary_status,
        )
    return RunDecision(True, False, "succeeded", summary_status)


def validate_dataset_count(summary: Any, item_count: Any) -> None:
    """Require one fetched dataset item for every summary-delivered row."""
    try:
        validated = validate_fleet_run_summary(summary)
    except FleetRunSummaryValidationError as exc:
        raise RunStateError(f"invalid RUN-SUMMARY: {exc}") from exc
    if type(item_count) is not int or item_count < 0:
        raise RunStateError("dataset item count must be a nonnegative integer")
    if validated["delivered"] != item_count:
        raise RunStateError(
            "RUN-SUMMARY delivered count does not match the fetched dataset"
        )


__all__ = [
    "RunDecision",
    "RunStateError",
    "TERMINAL_STATUSES",
    "evaluate_terminal_run",
    "validate_dataset_count",
]
