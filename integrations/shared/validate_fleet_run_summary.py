#!/usr/bin/env python3
"""Validate the canonical factual fleet-v2 ``RUN-SUMMARY`` contract.

Maintained integrations require this record before dataset delivery. The
validator checks facts only; neither ``retryable`` nor any other field
authorizes or schedules another paid Actor run.
"""

from __future__ import annotations

import datetime
import json
import re
import sys
from collections.abc import Mapping
from typing import Any


STATUSES = {"succeeded", "empty", "partial", "failed", "deadline"}
COUNTERS = (
    "cardsSeen", "detailsCompleted", "normalized", "afterFilters",
    "deliveryEligible", "delivered",
)
SOURCE_KEYS = {
    "status", "searchRequests", *COUNTERS, "stale", "blocked",
    "stopReason", "errors",
}
ERROR_KEYS = {"code", "stage", "retryable"}
ERROR_STAGES = {
    "validation", "search", "cards", "details", "normalization",
    "filtering", "enrichment", "translation", "deduplication", "inventory",
    "delivery", "billing", "summary", "runtime",
}
ROOT_KEYS = {
    "schemaVersion", "status", "startedAt", "finishedAt", "partial",
    "truncated", "delivered", "sources",
}
CODE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class FleetRunSummaryValidationError(ValueError):
    """Raised when a factual run-status record is inconsistent."""


def _closed(value: Any, path: str, keys: set[str]) -> Mapping[str, Any]:
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


def _source(value: Any, path: str) -> str:
    source = _closed(value, path, SOURCE_KEYS)
    status = source["status"]
    if status not in STATUSES:
        raise FleetRunSummaryValidationError(f"{path}.status is unsupported")
    _count(source["searchRequests"], f"{path}.searchRequests")
    counts = [_count(source[name], f"{path}.{name}") for name in COUNTERS]
    if any(left < right for left, right in zip(counts, counts[1:])):
        raise FleetRunSummaryValidationError(
            f"{path} counts must be monotonically non-increasing"
        )
    if type(source["stale"]) is not bool or type(source["blocked"]) is not bool:
        raise FleetRunSummaryValidationError(f"{path} flags must be boolean")
    if not isinstance(source["errors"], list) or len(source["errors"]) > 32:
        raise FleetRunSummaryValidationError(f"{path}.errors is invalid")
    for index, value in enumerate(source["errors"]):
        error_path = f"{path}.errors[{index}]"
        error = _closed(value, error_path, ERROR_KEYS)
        if not isinstance(error["code"], str) or CODE.fullmatch(error["code"]) is None:
            raise FleetRunSummaryValidationError(f"{error_path}.code is invalid")
        if error["stage"] not in ERROR_STAGES:
            raise FleetRunSummaryValidationError(f"{error_path}.stage is unsupported")
        if type(error["retryable"]) is not bool:
            raise FleetRunSummaryValidationError(
                f"{error_path}.retryable must be boolean"
            )
    if status == "empty" and (
        any(counts) or source["errors"] or source["blocked"] or source["stale"]
    ):
        raise FleetRunSummaryValidationError(
            f"{path} with empty status cannot report cards or degradation"
        )
    if source["blocked"] and status not in {"partial", "failed", "deadline"}:
        raise FleetRunSummaryValidationError(
            f"{path}.blocked requires partial, failed, or deadline status"
        )
    stop = source["stopReason"]
    if stop is not None and (not isinstance(stop, str) or CODE.fullmatch(stop) is None):
        raise FleetRunSummaryValidationError(f"{path}.stopReason is invalid")
    if (source["blocked"] or status in {"partial", "failed", "deadline"}) and stop is None:
        raise FleetRunSummaryValidationError(f"{path} requires a stopReason")
    if source["stale"] and status != "partial":
        raise FleetRunSummaryValidationError(f"{path}.stale requires partial status")
    if status == "failed" and source["delivered"]:
        raise FleetRunSummaryValidationError(f"{path} failed source cannot deliver records")
    return status


def validate_fleet_run_summary(value: Any) -> Mapping[str, Any]:
    summary = _closed(value, "summary", ROOT_KEYS)
    if summary["schemaVersion"] != "nomad-agent-fleet-run-summary-v2":
        raise FleetRunSummaryValidationError("summary.schemaVersion is unsupported")
    if summary["status"] not in STATUSES:
        raise FleetRunSummaryValidationError("summary.status is unsupported")
    if _time(summary["finishedAt"], "summary.finishedAt") < _time(
        summary["startedAt"], "summary.startedAt"
    ):
        raise FleetRunSummaryValidationError("summary.finishedAt cannot precede startedAt")
    if type(summary["partial"]) is not bool or type(summary["truncated"]) is not bool:
        raise FleetRunSummaryValidationError("summary flags must be boolean")
    delivered = _count(summary["delivered"], "summary.delivered")
    sources = summary["sources"]
    if not isinstance(sources, Mapping) or not sources:
        raise FleetRunSummaryValidationError("summary.sources must not be empty")
    if len(sources) > 128:
        raise FleetRunSummaryValidationError("summary.sources has too many entries")
    for name in sources:
        if (
            not isinstance(name, str)
            or not 1 <= len(name) <= 64
            or re.fullmatch(r"^[a-z0-9][a-z0-9._-]*$", name) is None
        ):
            raise FleetRunSummaryValidationError("summary source name is invalid")
    statuses = [_source(source, f"summary.sources.{name}") for name, source in sources.items()]
    if delivered != sum(source["delivered"] for source in sources.values()):
        raise FleetRunSummaryValidationError(
            "summary.delivered must equal the sum of sources[*].delivered"
        )
    if any(status == "partial" for status in statuses):
        derived = "partial"
    else:
        degraded = any(status in {"failed", "deadline"} for status in statuses)
        usable = any(status in {"succeeded", "empty"} for status in statuses)
        if degraded and usable:
            derived = "partial"
        elif degraded and all(status == "deadline" for status in statuses):
            derived = "deadline"
        elif degraded:
            derived = "failed"
        elif any(status == "succeeded" for status in statuses):
            derived = "succeeded"
        else:
            derived = "empty"
    root_status = summary["status"]
    if root_status not in {derived, "failed", "deadline"}:
        raise FleetRunSummaryValidationError("summary.status contradicts source status")
    if root_status in {"failed", "deadline"} and derived in {"failed", "deadline"}:
        pass
    elif root_status in {"failed", "deadline"} and derived not in {
        "succeeded", "empty", "partial"
    }:
        raise FleetRunSummaryValidationError("summary terminal status is inconsistent")
    expected_partial = root_status in {"partial", "deadline"} or (
        root_status == "failed" and delivered > 0
    )
    if summary["partial"] is not expected_partial:
        raise FleetRunSummaryValidationError("summary.partial contradicts status")
    return summary


def main() -> int:
    try:
        validate_fleet_run_summary(json.load(sys.stdin))
    except (json.JSONDecodeError, FleetRunSummaryValidationError) as exc:
        print(f"invalid fleet run summary: {exc}", file=sys.stderr)
        return 1
    print("valid fleet run summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
