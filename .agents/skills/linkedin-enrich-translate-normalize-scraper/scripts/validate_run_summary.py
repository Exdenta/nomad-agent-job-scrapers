#!/usr/bin/env python3
"""Validate the closed factual fleet-v2 RUN-SUMMARY contract."""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

STATUSES = {"succeeded", "empty", "partial", "failed", "deadline"}
STAGES = {
    "validation", "search", "cards", "details", "normalization", "filtering",
    "enrichment", "translation", "deduplication", "inventory", "delivery",
    "billing", "summary", "runtime",
}
COUNTERS = (
    "cardsSeen", "detailsCompleted", "normalized", "afterFilters",
    "deliveryEligible", "delivered",
)
ROOT_KEYS = {
    "schemaVersion", "status", "startedAt", "finishedAt", "partial",
    "truncated", "delivered", "sources",
}
SOURCE_KEYS = {
    "status", "searchRequests", *COUNTERS, "stale", "blocked", "stopReason",
    "errors",
}
ERROR_KEYS = {"code", "stage", "retryable"}
CODE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SOURCE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class FleetRunSummaryValidationError(ValueError):
    pass


def _object(value: Any, path: str, keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise FleetRunSummaryValidationError(f"{path} must be a closed object")
    return value


def _count(value: Any, path: str) -> int:
    if type(value) is not int or not 0 <= value <= 2_147_483_647:
        raise FleetRunSummaryValidationError(f"{path} must be a nonnegative integer")
    return value


def _time(value: Any, path: str) -> datetime.datetime:
    if not isinstance(value, str):
        raise FleetRunSummaryValidationError(f"{path} must be an ISO datetime")
    try:
        parsed = datetime.datetime.fromisoformat(
            value[:-1] + "+00:00" if value.endswith("Z") else value
        )
    except ValueError as exc:
        raise FleetRunSummaryValidationError(f"{path} must be an ISO datetime") from exc
    if parsed.tzinfo is None:
        raise FleetRunSummaryValidationError(f"{path} must include a timezone")
    return parsed


def _validate_source(value: Any, path: str) -> str:
    source = _object(value, path, SOURCE_KEYS)
    status = source["status"]
    if status not in STATUSES:
        raise FleetRunSummaryValidationError(f"{path}.status is unsupported")
    _count(source["searchRequests"], f"{path}.searchRequests")
    counts = [_count(source[name], f"{path}.{name}") for name in COUNTERS]
    if any(left < right for left, right in zip(counts, counts[1:])):
        raise FleetRunSummaryValidationError(f"{path} funnel is not monotonic")
    if type(source["stale"]) is not bool or type(source["blocked"]) is not bool:
        raise FleetRunSummaryValidationError(f"{path} flags must be boolean")
    errors = source["errors"]
    if not isinstance(errors, list) or len(errors) > 32:
        raise FleetRunSummaryValidationError(f"{path}.errors is invalid")
    for index, value in enumerate(errors):
        error = _object(value, f"{path}.errors[{index}]", ERROR_KEYS)
        if not isinstance(error["code"], str) or CODE.fullmatch(error["code"]) is None:
            raise FleetRunSummaryValidationError(f"{path}.errors[{index}].code is invalid")
        if error["stage"] not in STAGES or type(error["retryable"]) is not bool:
            raise FleetRunSummaryValidationError(f"{path}.errors[{index}] is invalid")
    stop = source["stopReason"]
    if stop is not None and (not isinstance(stop, str) or CODE.fullmatch(stop) is None):
        raise FleetRunSummaryValidationError(f"{path}.stopReason is invalid")
    degraded = status in {"partial", "failed", "deadline"}
    if degraded and stop is None:
        raise FleetRunSummaryValidationError(f"{path} degraded status requires stopReason")
    if status == "empty" and (
        any(counts) or errors or source["stale"] or source["blocked"] or stop is not None
    ):
        raise FleetRunSummaryValidationError(f"{path} empty status is degraded")
    if source["stale"] and status != "partial":
        raise FleetRunSummaryValidationError(f"{path}.stale requires partial status")
    if source["blocked"] and not degraded:
        raise FleetRunSummaryValidationError(f"{path}.blocked requires degraded status")
    if status == "failed" and source["delivered"]:
        raise FleetRunSummaryValidationError(f"{path} failed source delivered records")
    return status


def validate_fleet_run_summary(value: Any) -> Mapping[str, Any]:
    summary = _object(value, "summary", ROOT_KEYS)
    if summary["schemaVersion"] != "nomad-agent-fleet-run-summary-v2":
        raise FleetRunSummaryValidationError("summary.schemaVersion is unsupported")
    status = summary["status"]
    if status not in STATUSES:
        raise FleetRunSummaryValidationError("summary.status is unsupported")
    if _time(summary["finishedAt"], "summary.finishedAt") < _time(
        summary["startedAt"], "summary.startedAt"
    ):
        raise FleetRunSummaryValidationError("summary timestamps are reversed")
    if type(summary["partial"]) is not bool or type(summary["truncated"]) is not bool:
        raise FleetRunSummaryValidationError("summary flags must be boolean")
    delivered = _count(summary["delivered"], "summary.delivered")
    sources = summary["sources"]
    if not isinstance(sources, Mapping) or not 1 <= len(sources) <= 128:
        raise FleetRunSummaryValidationError("summary.sources is invalid")
    statuses = []
    for name, source in sources.items():
        if not isinstance(name, str) or not 1 <= len(name) <= 64 or SOURCE.fullmatch(name) is None:
            raise FleetRunSummaryValidationError("summary source name is invalid")
        statuses.append(_validate_source(source, f"summary.sources.{name}"))
    if delivered != sum(source["delivered"] for source in sources.values()):
        raise FleetRunSummaryValidationError("summary.delivered does not match sources")
    if "partial" in statuses:
        derived = "partial"
    elif any(item in {"failed", "deadline"} for item in statuses):
        derived = (
            "partial" if any(item in {"succeeded", "empty"} for item in statuses)
            else "deadline" if all(item == "deadline" for item in statuses)
            else "failed"
        )
    else:
        derived = "succeeded" if "succeeded" in statuses else "empty"
    if status != derived and status not in {"failed", "deadline"}:
        raise FleetRunSummaryValidationError("summary.status contradicts sources")
    expected_partial = status in {"partial", "deadline"} or (
        status == "failed" and delivered > 0
    )
    if summary["partial"] is not expected_partial:
        raise FleetRunSummaryValidationError("summary.partial contradicts status")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path)
    args = parser.parse_args()
    try:
        text = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
        validate_fleet_run_summary(json.loads(text))
    except (OSError, json.JSONDecodeError, FleetRunSummaryValidationError) as exc:
        print(f"invalid fleet run summary: {exc}", file=sys.stderr)
        return 1
    print("valid fleet run summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
