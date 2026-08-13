#!/usr/bin/env python3
"""Validate the minimal public ``nomad-agent-run-summary-v3`` contract."""
from __future__ import annotations

import datetime
import json
import sys
from collections.abc import Mapping
from typing import Any


ROOT_KEYS = {
    "schemaVersion", "status", "startedAt", "finishedAt", "truncated",
    "delivered", "retry",
}
RETRY_KEYS = {"recommended", "afterSeconds", "notBefore"}
STATUSES = {"succeeded", "empty", "partial"}
MAX_COUNTER = 2_147_483_647
MAX_RETRY_AFTER_SECONDS = 3_600


class RunSummaryValidationError(ValueError):
    """Raised when the public run outcome is malformed or contradictory."""


def _closed(value: Any, path: str, keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise RunSummaryValidationError(f"{path} must be a closed object")
    return value


def _time(value: Any, path: str) -> datetime.datetime:
    if not isinstance(value, str):
        raise RunSummaryValidationError(f"{path} must be an ISO datetime")
    try:
        parsed = datetime.datetime.fromisoformat(
            value[:-1] + "+00:00" if value.endswith("Z") else value
        )
    except ValueError as exc:
        raise RunSummaryValidationError(f"{path} must be an ISO datetime") from exc
    if parsed.tzinfo is None:
        raise RunSummaryValidationError(f"{path} must include a timezone")
    return parsed.astimezone(datetime.timezone.utc)


def _count(value: Any, path: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_COUNTER:
        raise RunSummaryValidationError(f"{path} must be a nonnegative integer")
    return value


def validate_run_summary(value: Any) -> Mapping[str, Any]:
    summary = _closed(value, "summary", ROOT_KEYS)
    if summary["schemaVersion"] != "nomad-agent-run-summary-v3":
        raise RunSummaryValidationError("summary.schemaVersion is unsupported")
    status = summary["status"]
    if status not in STATUSES:
        raise RunSummaryValidationError("summary.status is unsupported")
    started = _time(summary["startedAt"], "summary.startedAt")
    finished = _time(summary["finishedAt"], "summary.finishedAt")
    if finished < started:
        raise RunSummaryValidationError("summary.finishedAt cannot precede startedAt")
    if type(summary["truncated"]) is not bool:
        raise RunSummaryValidationError("summary.truncated must be boolean")
    delivered = _count(summary["delivered"], "summary.delivered")

    retry = _closed(summary["retry"], "summary.retry", RETRY_KEYS)
    recommended = retry["recommended"]
    if type(recommended) is not bool:
        raise RunSummaryValidationError("summary.retry.recommended must be boolean")
    if recommended:
        after = retry["afterSeconds"]
        if (
            type(after) is not int
            or not 1 <= after <= MAX_RETRY_AFTER_SECONDS
        ):
            raise RunSummaryValidationError(
                "summary.retry.afterSeconds must be an integer from 1 through 3600"
            )
        not_before = _time(retry["notBefore"], "summary.retry.notBefore")
        if not_before < finished:
            raise RunSummaryValidationError(
                "summary.retry.notBefore cannot precede finishedAt"
            )
    elif retry["afterSeconds"] is not None or retry["notBefore"] is not None:
        raise RunSummaryValidationError(
            "a non-recommended retry requires null timing fields"
        )

    if status == "empty":
        if delivered != 0 or summary["truncated"] or recommended:
            raise RunSummaryValidationError(
                "empty requires delivered=0, truncated=false, and no retry"
            )
    elif delivered < 1:
        raise RunSummaryValidationError(
            "succeeded and partial outcomes require at least one delivered job"
        )
    if status == "succeeded" and recommended:
        raise RunSummaryValidationError("succeeded cannot recommend a retry")
    return summary


def main() -> int:
    try:
        validate_run_summary(json.load(sys.stdin))
    except (json.JSONDecodeError, RunSummaryValidationError) as exc:
        print(f"invalid run summary: {exc}", file=sys.stderr)
        return 1
    print("valid run summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
