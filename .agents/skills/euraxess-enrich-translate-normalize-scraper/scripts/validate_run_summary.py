#!/usr/bin/env python3
"""Validate the minimal public nomad-agent-run-summary-v4 contract."""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT_KEYS = {
    "schemaVersion", "status", "startedAt", "finishedAt", "resultsLimited",
    "delivered", "retry",
}
RETRY_KEYS = {"recommended", "afterSeconds"}
STATUSES = {"succeeded", "empty", "empty-limited", "partial"}


class RunSummaryValidationError(ValueError):
    pass


def _object(value: Any, path: str, keys: set[str]) -> Mapping[str, Any]:
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
    if type(value) is not int or not 0 <= value <= 2_147_483_647:
        raise RunSummaryValidationError(f"{path} must be a nonnegative integer")
    return value


def validate_run_summary(value: Any) -> Mapping[str, Any]:
    summary = _object(value, "summary", ROOT_KEYS)
    if summary["schemaVersion"] != "nomad-agent-run-summary-v4":
        raise RunSummaryValidationError("summary.schemaVersion is unsupported")
    status = summary["status"]
    if status not in STATUSES:
        raise RunSummaryValidationError("summary.status is unsupported")
    started = _time(summary["startedAt"], "summary.startedAt")
    finished = _time(summary["finishedAt"], "summary.finishedAt")
    if finished < started:
        raise RunSummaryValidationError("summary timestamps are reversed")
    if type(summary["resultsLimited"]) is not bool:
        raise RunSummaryValidationError("summary.resultsLimited must be boolean")
    delivered = _count(summary["delivered"], "summary.delivered")
    retry = _object(summary["retry"], "summary.retry", RETRY_KEYS)
    recommended = retry["recommended"]
    if type(recommended) is not bool:
        raise RunSummaryValidationError("summary.retry.recommended must be boolean")
    if recommended:
        after = retry["afterSeconds"]
        if type(after) is not int or not 1 <= after <= 3_600:
            raise RunSummaryValidationError(
                "summary.retry.afterSeconds must be an integer from 1 through 3600"
            )
    elif retry["afterSeconds"] is not None:
        raise RunSummaryValidationError(
            "a non-recommended retry requires afterSeconds=null"
        )
    if status == "empty":
        if delivered != 0 or summary["resultsLimited"] or recommended:
            raise RunSummaryValidationError(
                "empty requires delivered=0, resultsLimited=false, and no retry"
            )
    elif status == "empty-limited":
        if delivered != 0 or not summary["resultsLimited"] or recommended:
            raise RunSummaryValidationError("empty-limited requires zero rows, resultsLimited=true, and no retry")
    elif delivered < 1:
        raise RunSummaryValidationError(
            "succeeded and partial require at least one delivered job"
        )
    if status == "succeeded" and recommended:
        raise RunSummaryValidationError("succeeded cannot recommend a retry")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path)
    args = parser.parse_args()
    try:
        text = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
        validate_run_summary(json.loads(text))
    except (OSError, json.JSONDecodeError, RunSummaryValidationError) as exc:
        print(f"invalid run summary: {exc}", file=sys.stderr)
        return 1
    print("valid run summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
