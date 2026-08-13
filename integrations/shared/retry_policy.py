"""Strict one-retry policy for the minimal public RUN-SUMMARY v4."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from validate_run_summary import (
    RunSummaryValidationError,
    validate_run_summary,
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
    delay_seconds: int = 0


def evaluate_terminal_run(
    run: Any,
    summary: Any = None,
    *,
    retry_attempt: int = 0,
    max_retries: int = 1,
) -> RunDecision:
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
    if type(retry_attempt) is not int or type(max_retries) is not int:
        raise RunStateError("retry bounds must be integers")
    if retry_attempt < 0 or max_retries not in {0, 1} or retry_attempt > max_retries:
        raise RunStateError("retry bounds allow at most one retry")
    try:
        validated = validate_run_summary(summary)
    except RunSummaryValidationError as exc:
        raise RunStateError(f"invalid RUN-SUMMARY: {exc}") from exc
    summary_status = str(validated["status"])
    retry = validated["retry"]
    if retry["recommended"] and retry_attempt < max_retries:
        delay = int(retry["afterSeconds"])
        return RunDecision(
            False,
            True,
            "retry-recommended",
            summary_status,
            delay,
        )
    reason = (
        "retry-bound-exhausted"
        if retry["recommended"] and retry_attempt >= max_retries
        else summary_status
    )
    return RunDecision(True, False, reason, summary_status)


def validate_dataset_count(summary: Any, item_count: Any) -> None:
    """Require one fetched dataset item for every summary-delivered row."""
    try:
        validated = validate_run_summary(summary)
    except RunSummaryValidationError as exc:
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
