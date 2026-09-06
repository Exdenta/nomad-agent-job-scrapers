#!/usr/bin/env python3
"""Validate a nomad-ai-job-fit-run-summary-v4 record from the AI Job Search & Fit Scorer.

Usage:
    python3 validate_run_summary.py run-summary.json
    cat run-summary.json | python3 validate_run_summary.py

Exit code 0 means the record is a usable v4 summary whose counts, result
policy, provider guard, and billing receipt reconcile. Exit code 1 prints the
first violation. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from typing import Any

sys.dont_write_bytecode = True

from schema_check import validate_schema, read_json

SCHEMA_VERSION = "nomad-ai-job-fit-run-summary-v4"
USABLE_STATUSES = {"complete", "partial", "empty"}
COUNT_NAMES = (
    "sourceJobs",
    "budgetAuthorizedJobs",
    "evaluatedJobs",
    "staticDropped",
    "staticHeld",
    "aiAttempted",
    "aiScored",
    "aiFailed",
    "resultFilteredOut",
    "outputRows",
)
BILLING_KEYS = {
    "budgetAuthorizedCount",
    "budgetLimited",
    "chargedCount",
    "eventName",
    "totalChargedUsd",
    "unitPriceUsd",
}


class RunSummaryValidationError(ValueError):
    pass


def _fail(message: str) -> None:
    raise RunSummaryValidationError(message)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{path} must be an object")
    return value


def _count(value: Any, path: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{path} must be a non-negative integer")
    return value


def validate_run_summary(
    value: Any, *, expected_build: str | None = None
) -> Mapping[str, Any]:
    try:
        validate_schema(value, "nomad-ai-job-fit-run-summary-v4.schema.json", "summary")
    except ValueError as exc:
        _fail(str(exc))
    summary = _mapping(value, "summary")
    if summary.get("schemaVersion") != SCHEMA_VERSION:
        _fail(f"summary.schemaVersion must be {SCHEMA_VERSION}")
    if summary.get("recordType") != "RUN-SUMMARY":
        _fail("summary.recordType must be RUN-SUMMARY")
    status = summary.get("status")
    if status not in USABLE_STATUSES:
        _fail(f"summary.status {status!r} is not usable")

    actor = _mapping(summary.get("actor"), "summary.actor")
    if expected_build and actor.get("buildNumber") != expected_build:
        _fail(
            f"summary.actor.buildNumber {actor.get('buildNumber')!r} differs from "
            f"expected build {expected_build!r}"
        )

    algorithm = _mapping(summary.get("algorithm"), "summary.algorithm")
    if algorithm.get("name") != "scoring-v3":
        _fail("summary.algorithm.name must be scoring-v3")
    if algorithm.get("interactionStateUsed") is not False:
        _fail("summary.algorithm.interactionStateUsed must be false")

    counts = _mapping(summary.get("counts"), "summary.counts")
    values = {name: _count(counts.get(name), f"summary.counts.{name}") for name in COUNT_NAMES}
    if not values["evaluatedJobs"] <= values["budgetAuthorizedJobs"] <= values["sourceJobs"]:
        _fail("summary.counts must satisfy evaluatedJobs <= budgetAuthorizedJobs <= sourceJobs")
    if summary["cleanEmpty"] and (values["sourceJobs"] or values["evaluatedJobs"]):
        _fail("summary.cleanEmpty requires zero source and evaluated jobs")
    if summary["status"] == "empty" and values["outputRows"]:
        _fail("summary.status empty requires zero output rows")
    if (
        values["staticDropped"] + values["staticHeld"] + values["aiScored"] + values["aiFailed"]
        != values["evaluatedJobs"]
    ):
        _fail("summary.counts do not partition evaluatedJobs")
    if values["aiScored"] + values["aiFailed"] != values["aiAttempted"]:
        _fail("summary.counts.aiAttempted must equal aiScored + aiFailed")
    if values["resultFilteredOut"] + values["outputRows"] != values["evaluatedJobs"]:
        _fail("summary.counts filtered and output rows do not reconcile")

    parameters = _mapping(summary.get("parameters"), "summary.parameters")
    result_mode = parameters.get("resultMode")
    threshold = parameters.get("minDeliveryScore")
    if result_mode not in {"shortlist", "audit"}:
        _fail("summary.parameters.resultMode must be shortlist or audit")
    if type(threshold) is not int or not 0 <= threshold <= 5:
        _fail("summary.parameters.minDeliveryScore must be an integer from 0 to 5")
    if result_mode == "shortlist" and values["outputRows"] > values["aiScored"]:
        _fail("shortlist outputRows cannot exceed aiScored")
    if result_mode == "audit" and (
        values["resultFilteredOut"] != 0 or values["outputRows"] != values["evaluatedJobs"]
    ):
        _fail("audit mode must retain every evaluated row")

    ai = _mapping(summary.get("ai"), "summary.ai")
    if ai.get("providerCostLimitUsd") != 0.25:
        _fail("summary.ai.providerCostLimitUsd must be 0.25")
    if ai.get("maxProviderAttempts") != 2:
        _fail("summary.ai.maxProviderAttempts must be 2")
    if not isinstance(ai.get("providerCostLimited"), bool):
        _fail("summary.ai.providerCostLimited must be a boolean")
    reserved = ai.get("providerCostReservedUsd")
    if not isinstance(reserved, (int, float)) or isinstance(reserved, bool) or not 0 <= reserved <= 0.25:
        _fail("summary.ai.providerCostReservedUsd must be between 0 and 0.25")

    billing = _mapping(summary.get("billing"), "summary.billing")
    if set(billing) != BILLING_KEYS:
        _fail("summary.billing must contain exactly the six receipt fields")
    if billing.get("eventName") != "job-fit-result":
        _fail("summary.billing.eventName must be job-fit-result")
    if billing.get("unitPriceUsd") != 0.02:
        _fail("summary.billing.unitPriceUsd must be 0.02")
    if billing["budgetAuthorizedCount"] != values["budgetAuthorizedJobs"]:
        _fail("summary.billing budget authorization does not match counts")
    charged = _count(billing.get("chargedCount"), "summary.billing.chargedCount")
    expected_charged = (
        values["outputRows"] if result_mode == "shortlist" else values["outputRows"] - values["aiFailed"]
    )
    if charged != expected_charged:
        _fail(
            f"summary.billing.chargedCount {charged} does not match the {result_mode} "
            f"policy (expected {expected_charged})"
        )
    total = billing.get("totalChargedUsd")
    if not isinstance(total, (int, float)) or isinstance(total, bool) or abs(total - charged * 0.02) > 1e-9:
        _fail("summary.billing.totalChargedUsd must equal chargedCount × 0.02")

    candidate = _mapping(summary.get("candidate"), "summary.candidate")
    for key in ("candidateHash", "candidateSnapshotHash", "derivedFromResume", "resumeChars"):
        if key not in candidate:
            _fail(f"summary.candidate.{key} is missing")

    for key in ("candidateHash", "candidateSnapshotHash"):
        import re
        digest = candidate[key]
        if values["evaluatedJobs"] and (not isinstance(digest, str) or re.fullmatch(r"[a-f0-9]{64}", digest) is None):
            _fail(f"summary.candidate.{key} must be a sha256 for evaluated jobs")
    terminal = _mapping(summary.get("terminal"), "summary.terminal")
    if not isinstance(terminal.get("reason"), str):
        _fail("summary.terminal.reason must be a string")
    if not isinstance(summary.get("warnings"), list):
        _fail("summary.warnings must be an array")
    return summary


def validate_run_receipt(summary: Mapping[str, Any], value: Any, *, expected_build: str | None = None) -> None:
    run = _mapping(value, "run")
    run = _mapping(run.get("data", run), "run")
    validate_run_summary(summary, expected_build=expected_build)
    if run.get("status") != "SUCCEEDED" or type(run.get("exitCode")) is not int or run["exitCode"] != 0:
        _fail("run must be SUCCEEDED with exitCode 0")
    for summary_key, run_key in (("id", "actId"), ("runId", "id"), ("buildId", "buildId"), ("buildNumber", "buildNumber")):
        expected = summary["actor"].get(summary_key)
        if not isinstance(expected, str) or not expected or run.get(run_key) != expected:
            _fail(f"run.{run_key} does not match summary.actor.{summary_key}")
    for key in ("defaultDatasetId", "defaultKeyValueStoreId"):
        if not isinstance(run.get(key), str) or not run[key]:
            _fail(f"run.{key} is missing")
    charges = _mapping(run.get("chargedEventCounts"), "run.chargedEventCounts")
    charged = _count(charges.get("job-fit-result", 0), "run.chargedEventCounts.job-fit-result")
    if charged != summary["billing"]["chargedCount"]:
        _fail("run charge count does not reconcile with summary")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", help="RUN-SUMMARY JSON file; stdin when omitted")
    parser.add_argument("--expected-build", default=None, help="Build number the run must report")
    parser.add_argument("--run", help="Authoritative Apify run JSON receipt")
    args = parser.parse_args()
    try:
        summary = validate_run_summary(read_json(args.path), expected_build=args.expected_build)
        if args.run:
            validate_run_receipt(summary, read_json(args.run), expected_build=args.expected_build)
    except (ValueError, OSError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    counts = summary["counts"]
    report = {
        "status": summary["status"], "build": summary["actor"].get("buildNumber"),
        "resultMode": summary["parameters"]["resultMode"],
        "evaluatedJobs": counts["evaluatedJobs"], "outputRows": counts["outputRows"],
        "resultFilteredOut": counts["resultFilteredOut"], "aiFailed": counts["aiFailed"],
        "chargedUsd": summary["billing"]["totalChargedUsd"],
        "usedExampleProfile": summary["candidate"].get("usedExampleProfile", False),
        "warnings": summary["warnings"],
    }
    if report["usedExampleProfile"]:
        print("warning: this run scored the built-in example candidate, not a supplied one", file=sys.stderr)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
