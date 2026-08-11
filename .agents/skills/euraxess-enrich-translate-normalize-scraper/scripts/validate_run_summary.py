#!/usr/bin/env python3
"""Validate structural and cross-field fleet-v2 RUN-SUMMARY semantics."""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "nomad-agent-fleet-run-summary-v2"
STATUSES = frozenset({"succeeded", "empty", "partial", "failed", "deadline"})
ERROR_STAGES = frozenset(
    {
        "validation",
        "search",
        "cards",
        "details",
        "normalization",
        "filtering",
        "enrichment",
        "translation",
        "deduplication",
        "inventory",
        "delivery",
        "billing",
        "summary",
        "runtime",
    }
)
COUNTER_FIELDS = (
    "cardsSeen",
    "detailsCompleted",
    "normalized",
    "afterFilters",
    "deliveryEligible",
    "delivered",
)
MAX_COUNTER = 2_147_483_647
CODE_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SOURCE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class FleetRunSummaryValidationError(ValueError):
    """Raised when a fleet-v2 summary violates its public wire contract."""


def _object(value: Any, path: str, keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FleetRunSummaryValidationError(f"{path} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise FleetRunSummaryValidationError(f"{path} keys must be strings")
    actual = set(value)
    if actual != keys:
        raise FleetRunSummaryValidationError(
            f"{path} has missing keys {sorted(keys - actual)!r} "
            f"and extra keys {sorted(actual - keys)!r}"
        )
    return value


def _boolean(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise FleetRunSummaryValidationError(f"{path} must be a boolean")
    return value


def _counter(value: Any, path: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_COUNTER:
        raise FleetRunSummaryValidationError(
            f"{path} must be an integer from 0 through {MAX_COUNTER}"
        )
    return value


def _status(value: Any, path: str) -> str:
    if not isinstance(value, str) or value not in STATUSES:
        raise FleetRunSummaryValidationError(
            f"{path} must be one of {sorted(STATUSES)!r}"
        )
    return value


def _code(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 64
        or CODE_RE.fullmatch(value) is None
    ):
        suffix = " or null" if nullable else ""
        raise FleetRunSummaryValidationError(
            f"{path} must be a bounded lowercase machine code{suffix}"
        )
    return value


def _timestamp(value: Any, path: str) -> datetime.datetime:
    if not isinstance(value, str) or not value:
        raise FleetRunSummaryValidationError(
            f"{path} must be an ISO 8601 datetime with a timezone"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise FleetRunSummaryValidationError(
            f"{path} must be an ISO 8601 datetime with a timezone"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FleetRunSummaryValidationError(
            f"{path} must be an ISO 8601 datetime with a timezone"
        )
    return parsed.astimezone(datetime.timezone.utc)


def _error(value: Any, path: str) -> None:
    item = _object(value, path, {"code", "stage", "retryable"})
    _code(item["code"], f"{path}.code")
    if not isinstance(item["stage"], str) or item["stage"] not in ERROR_STAGES:
        raise FleetRunSummaryValidationError(
            f"{path}.stage must be a supported stable stage"
        )
    _boolean(item["retryable"], f"{path}.retryable")


def _source(value: Any, path: str) -> str:
    item = _object(
        value,
        path,
        {
            "status",
            "searchRequests",
            *COUNTER_FIELDS,
            "stale",
            "blocked",
            "stopReason",
            "errors",
        },
    )
    status = _status(item["status"], f"{path}.status")
    _counter(item["searchRequests"], f"{path}.searchRequests")
    counts = [_counter(item[field], f"{path}.{field}") for field in COUNTER_FIELDS]
    stale = _boolean(item["stale"], f"{path}.stale")
    blocked = _boolean(item["blocked"], f"{path}.blocked")
    stop_reason = _code(item["stopReason"], f"{path}.stopReason", nullable=True)
    errors = item["errors"]
    if not isinstance(errors, list) or len(errors) > 32:
        raise FleetRunSummaryValidationError(
            f"{path}.errors must be an array with at most 32 entries"
        )
    for index, error in enumerate(errors):
        _error(error, f"{path}.errors[{index}]")

    if any(left < right for left, right in zip(counts, counts[1:])):
        raise FleetRunSummaryValidationError(
            f"{path} counts must be monotonically non-increasing from "
            "cardsSeen through delivered"
        )
    if status == "empty":
        if any(counts):
            raise FleetRunSummaryValidationError(
                f"{path} with empty status cannot report cards or downstream records"
            )
        if errors or blocked or stale or stop_reason is not None:
            raise FleetRunSummaryValidationError(
                f"{path} with empty status cannot also be degraded"
            )
    if stale and status != "partial":
        raise FleetRunSummaryValidationError(
            f"{path}.stale requires partial status"
        )
    if blocked and status not in {"partial", "failed", "deadline"}:
        raise FleetRunSummaryValidationError(
            f"{path}.blocked requires partial, failed, or deadline status"
        )
    if blocked and stop_reason is None:
        raise FleetRunSummaryValidationError(
            f"{path}.blocked requires a stopReason"
        )
    if status in {"partial", "failed", "deadline"} and stop_reason is None:
        raise FleetRunSummaryValidationError(
            f"{path} with {status} status requires a stopReason"
        )
    if status == "failed" and item["delivered"]:
        raise FleetRunSummaryValidationError(
            f"{path} with failed status cannot report delivered records"
        )
    return status


def _derived_status(statuses: list[str]) -> str:
    if "partial" in statuses:
        return "partial"
    degraded = any(status in {"failed", "deadline"} for status in statuses)
    usable = any(status in {"succeeded", "empty"} for status in statuses)
    if degraded and usable:
        return "partial"
    if degraded:
        return "deadline" if all(status == "deadline" for status in statuses) else "failed"
    return "succeeded" if "succeeded" in statuses else "empty"


def validate_fleet_run_summary(value: Any) -> Mapping[str, Any]:
    """Return *value* after validating the closed fleet-v2 wire contract.

    The adjacent JSON Schema is intentionally structural. This function adds
    the canonical cross-field invariants that JSON Schema cannot express
    clearly, including count monotonicity, source status consistency, and
    aggregate delivery parity.
    """

    summary = _object(
        value,
        "summary",
        {
            "schemaVersion",
            "status",
            "startedAt",
            "finishedAt",
            "partial",
            "truncated",
            "delivered",
            "sources",
        },
    )
    if summary["schemaVersion"] != SCHEMA_VERSION:
        raise FleetRunSummaryValidationError(
            f"summary.schemaVersion must be {SCHEMA_VERSION}"
        )
    status = _status(summary["status"], "summary.status")
    started = _timestamp(summary["startedAt"], "summary.startedAt")
    finished = _timestamp(summary["finishedAt"], "summary.finishedAt")
    if finished < started:
        raise FleetRunSummaryValidationError(
            "summary.finishedAt cannot precede summary.startedAt"
        )
    partial = _boolean(summary["partial"], "summary.partial")
    _boolean(summary["truncated"], "summary.truncated")
    delivered = _counter(summary["delivered"], "summary.delivered")

    sources = summary["sources"]
    if not isinstance(sources, Mapping) or not 1 <= len(sources) <= 128:
        raise FleetRunSummaryValidationError(
            "summary.sources must contain 1 through 128 source objects"
        )
    statuses: list[str] = []
    source_delivered = 0
    for name, source in sources.items():
        if (
            not isinstance(name, str)
            or not 1 <= len(name) <= 64
            or SOURCE_RE.fullmatch(name) is None
        ):
            raise FleetRunSummaryValidationError(
                "summary source names must be bounded stable slugs"
            )
        statuses.append(_source(source, f"summary.sources.{name}"))
        source_delivered += source["delivered"]

    _counter(source_delivered, "sum of source delivered counts")
    if delivered != source_delivered:
        raise FleetRunSummaryValidationError(
            "summary.delivered must equal the sum of sources[*].delivered"
        )
    derived = _derived_status(statuses)
    if status != derived and status not in {"failed", "deadline"}:
        raise FleetRunSummaryValidationError(
            f"summary.status must be the derived {derived!r} status or an explicit "
            "terminal failed/deadline override"
        )
    expected_partial = status in {"partial", "deadline"} or (
        status == "failed" and delivered > 0
    )
    if partial is not expected_partial:
        raise FleetRunSummaryValidationError(
            f"summary.partial must be {expected_partial!r} for status={status!r} "
            f"and delivered={delivered}"
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="JSON file; omit for stdin")
    args = parser.parse_args()
    text = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
    try:
        validate_fleet_run_summary(json.loads(text))
    except (json.JSONDecodeError, FleetRunSummaryValidationError) as exc:
        print(f"invalid fleet run summary: {exc}", file=sys.stderr)
        return 1
    print("valid fleet run summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
