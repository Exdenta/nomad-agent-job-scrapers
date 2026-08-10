"""Strict, bounded retry policy for the LinkedIn Actor RUN-SUMMARY record."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from typing import Any


RUN_SUMMARY_SCHEMA_VERSION = "nomad-agent-linkedin-run-summary-v1"
MAX_RETRY_AFTER_SECONDS = 3_600


class RunSummaryError(ValueError):
    """Raised when a versioned run summary violates its retry contract."""


@dataclass(frozen=True, slots=True)
class RetryDecision:
    recommended: bool
    delay_seconds: int
    reason: str


def _parse_not_before(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise RunSummaryError("recommended retry requires reschedule.notBefore")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RunSummaryError("reschedule.notBefore must be an ISO date-time") from exc
    if parsed.tzinfo is None:
        raise RunSummaryError("reschedule.notBefore must include a timezone")
    return parsed.astimezone(timezone.utc)


def evaluate_run_summary(
    summary: Any,
    *,
    now: datetime | None = None,
) -> RetryDecision:
    """Return a retry decision without treating missing/legacy summaries as retryable."""
    if not isinstance(summary, dict) or not summary:
        return RetryDecision(False, 0, "missing-summary")
    schema_version = summary.get("schemaVersion")
    if schema_version is None:
        return RetryDecision(False, 0, "missing-summary")
    if schema_version != RUN_SUMMARY_SCHEMA_VERSION:
        raise RunSummaryError(f"unsupported run summary schema: {schema_version!r}")

    blocked = summary.get("blocked")
    reschedule = summary.get("reschedule")
    if not isinstance(blocked, bool) or not isinstance(reschedule, dict):
        raise RunSummaryError("versioned run summary has invalid retry fields")
    recommended = reschedule.get("recommended")
    if not isinstance(recommended, bool):
        raise RunSummaryError("reschedule.recommended must be boolean")
    if not recommended:
        return RetryDecision(False, 0, "not-recommended")
    if blocked is not True:
        raise RunSummaryError("recommended retry requires blocked=true")

    after_seconds = reschedule.get("afterSeconds")
    if (
        isinstance(after_seconds, bool)
        or not isinstance(after_seconds, int)
        or not 1 <= after_seconds <= MAX_RETRY_AFTER_SECONDS
    ):
        raise RunSummaryError("reschedule.afterSeconds must be an integer from 1 to 3600")
    not_before = _parse_not_before(reschedule.get("notBefore"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    remaining = max(0, ceil((not_before - current).total_seconds()))
    return RetryDecision(True, min(after_seconds, remaining), "actor-blocked")


__all__ = [
    "MAX_RETRY_AFTER_SECONDS",
    "RUN_SUMMARY_SCHEMA_VERSION",
    "RetryDecision",
    "RunSummaryError",
    "evaluate_run_summary",
]
