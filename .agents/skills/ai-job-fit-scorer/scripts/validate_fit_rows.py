#!/usr/bin/env python3
"""Validate nomad-ai-job-fit-v1 dataset rows from the AI Job Search & Fit Scorer.

Usage:
    python3 validate_fit_rows.py dataset.json
    python3 validate_fit_rows.py dataset.json --summary run-summary.json --table

With --summary the row count, the shortlist or audit policy, and the charged
count are reconciled against the run's RUN-SUMMARY. With --table a compact
review table is printed after validation. Exit code 0 means every row is a
closed, well-formed evaluation. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from typing import Any

from schema_check import validate_schema, read_json
from validate_run_summary import validate_run_summary, validate_run_receipt

ROW_KEYS = {
    "blockingGates",
    "candidateHash",
    "candidateSnapshotHash",
    "company",
    "deliveryScore",
    "evaluatedAt",
    "evaluationKey",
    "evaluationStatus",
    "externalId",
    "fitScore",
    "gapSummary",
    "gates",
    "job",
    "jobKey",
    "location",
    "matchKey",
    "postedAt",
    "recommendation",
    "schemaVersion",
    "scoreAdjustedForGates",
    "scoring",
    "source",
    "staticDecision",
    "title",
    "url",
    "why",
}
STATUSES = {"scored", "static_drop", "static_hold", "forward_cap_hold", "ai_failed"}
RECOMMENDATIONS = {
    "exceptional",
    "strong",
    "plausible",
    "weak",
    "poor",
    "incompatible",
    "blocked",
    "held",
    "unavailable",
    None,
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class FitRowValidationError(ValueError):
    pass


def _fail(message: str) -> None:
    raise FitRowValidationError(message)


def _score(value: Any, path: str, maximum: int) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= maximum:
        _fail(f"{path} must be null or an integer from 0 to {maximum}")
    return value


def validate_row(row: Any, index: int) -> Mapping[str, Any]:
    path = f"rows[{index}]"
    if not isinstance(row, Mapping):
        _fail(f"{path} must be an object")
    try:
        validate_schema(row, "nomad-ai-job-fit-v1.schema.json", path)
    except ValueError as exc:
        _fail(str(exc))
    if set(row) != ROW_KEYS:
        missing = sorted(ROW_KEYS - set(row))
        extra = sorted(set(row) - ROW_KEYS)
        _fail(f"{path} keys differ from nomad-ai-job-fit-v1 (missing {missing}, extra {extra})")
    if row["schemaVersion"] != "nomad-ai-job-fit-v1":
        _fail(f"{path}.schemaVersion must be nomad-ai-job-fit-v1")
    for key in ("matchKey", "evaluationKey", "candidateHash", "candidateSnapshotHash"):
        if not isinstance(row[key], str) or not SHA256.match(row[key]):
            _fail(f"{path}.{key} must be a 64-character hex sha256")
    if not isinstance(row["jobKey"], str) or ":" not in row["jobKey"]:
        _fail(f"{path}.jobKey must look like source:externalId")
    if row["evaluationStatus"] not in STATUSES:
        _fail(f"{path}.evaluationStatus {row['evaluationStatus']!r} is unknown")
    fit = _score(row["fitScore"], f"{path}.fitScore", 100)
    delivery = _score(row["deliveryScore"], f"{path}.deliveryScore", 5)
    if row["recommendation"] not in RECOMMENDATIONS:
        _fail(f"{path}.recommendation {row['recommendation']!r} is unknown")
    if row["evaluationStatus"] == "scored" and (fit is None or delivery is None):
        _fail(f"{path} is scored but has a null score")
    if not isinstance(row["blockingGates"], list) or not all(
        isinstance(item, str) for item in row["blockingGates"]
    ):
        _fail(f"{path}.blockingGates must be an array of strings")
    if not isinstance(row["scoreAdjustedForGates"], bool):
        _fail(f"{path}.scoreAdjustedForGates must be a boolean")
    for key in ("why", "gapSummary"):
        if not isinstance(row[key], str):
            _fail(f"{path}.{key} must be a string")
    for key in ("gates", "staticDecision", "scoring", "job"):
        if not isinstance(row[key], Mapping):
            _fail(f"{path}.{key} must be an object")
    if row["job"].get("schemaVersion") != "nomad-agent-job-v1":
        _fail(f"{path}.job must be a nomad-agent-job-v1 record")
    if row["scoring"].get("algorithm") != "scoring-v3":
        _fail(f"{path}.scoring.algorithm must be scoring-v3")
    for key in ("identity", "data", "llm", "raw"):
        if not isinstance(row["job"].get(key), Mapping):
            _fail(f"{path}.job.{key} must be an object")
    identity = row["job"]["identity"]
    if row["source"] != identity.get("source") or row["externalId"] != identity.get("externalId"):
        _fail(f"{path} source identity differs from nested job")
    if row["externalId"] and row["jobKey"] != f"{row['source']}:{row['externalId']}":
        _fail(f"{path}.jobKey differs from source identity")
    if row["evaluationStatus"] in {"static_hold", "forward_cap_hold", "ai_failed"} and (fit is not None or delivery is not None):
        _fail(f"{path} unscored evaluation must not contain scores")
    if row["evaluationStatus"] == "static_drop" and (fit != 0 or delivery != 0):
        _fail(f"{path} static_drop requires explicit zero scores")
    return row


def validate_rows(
    rows: Any, summary: Mapping[str, Any] | None = None
) -> list[Mapping[str, Any]]:
    if not isinstance(rows, list):
        _fail("dataset must be a JSON array of rows")
    seen: set[str] = set()
    validated = []
    for index, row in enumerate(rows):
        row = validate_row(row, index)
        if row["matchKey"] in seen:
            _fail(f"rows[{index}].matchKey duplicates an earlier row")
        seen.add(row["matchKey"])
        validated.append(row)
    if summary is not None:
        validate_run_summary(summary)
        for index, row in enumerate(validated):
            for key in ("candidateHash", "candidateSnapshotHash"):
                if row[key] != summary["candidate"][key]:
                    _fail(f"rows[{index}].{key} differs from summary candidate")
            if row["evaluatedAt"] != summary["evaluationAsOf"]:
                _fail(f"rows[{index}].evaluatedAt differs from summary evaluationAsOf")
            if row["scoring"]["sourceProvenance"] != summary["source"]:
                _fail(f"rows[{index}] source provenance differs from summary")
        counts = summary.get("counts") or {}
        parameters = summary.get("parameters") or {}
        billing = summary.get("billing") or {}
        if counts.get("outputRows") != len(validated):
            _fail(
                f"dataset has {len(validated)} rows but RUN-SUMMARY.counts.outputRows is "
                f"{counts.get('outputRows')}"
            )
        mode = parameters.get("resultMode")
        threshold = parameters.get("minDeliveryScore")
        if mode == "shortlist":
            for index, row in enumerate(validated):
                if row["evaluationStatus"] != "scored" or row["deliveryScore"] < threshold:
                    _fail(f"rows[{index}] violates the shortlist policy (min delivery {threshold})")
            if billing.get("chargedCount") != len(validated):
                _fail("shortlist chargedCount must equal the number of returned rows")
        elif mode == "audit":
            for key, statuses in (("staticDropped", {"static_drop"}), ("staticHeld", {"static_hold", "forward_cap_hold"}), ("aiScored", {"scored"}), ("aiFailed", {"ai_failed"})):
                if sum(row["evaluationStatus"] in statuses for row in validated) != counts[key]:
                    _fail(f"audit dataset does not reconcile {key}")
            billable = sum(1 for row in validated if row["evaluationStatus"] != "ai_failed")
            if billing.get("chargedCount") != billable:
                _fail("audit chargedCount must equal the number of non-failure rows")
    return validated


def table(rows: list[Mapping[str, Any]]) -> str:
    header = ("delivery", "fit", "recommendation", "status", "title", "company", "location", "gates", "url")
    lines = ["\t".join(header)]
    for row in sorted(rows, key=lambda r: (r["deliveryScore"] if r["deliveryScore"] is not None else -1, r["fitScore"] if r["fitScore"] is not None else -1), reverse=True):
        lines.append(
            "\t".join(
                str(value).replace("\t", " ").replace("\n", " ").replace("\r", " ") if value is not None else ""
                for value in (
                    row["deliveryScore"],
                    row["fitScore"],
                    row["recommendation"],
                    row["evaluationStatus"],
                    row["title"],
                    row["company"],
                    row["location"],
                    ",".join(row["blockingGates"]),
                    row["url"],
                )
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", help="dataset JSON array; stdin when omitted")
    parser.add_argument("--summary", help="RUN-SUMMARY JSON file to reconcile against")
    parser.add_argument("--run", help="Authoritative Apify run JSON receipt; requires --summary")
    parser.add_argument("--table", action="store_true", help="print a review table")
    args = parser.parse_args()
    try:
        if args.run and not args.summary:
            _fail("--run requires --summary")
        summary = read_json(args.summary) if args.summary else None
        if args.run:
            validate_run_receipt(summary, read_json(args.run))
        rows = validate_rows(read_json(args.path), summary)
    except (ValueError, OSError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    print(f"valid: {len(rows)} nomad-ai-job-fit-v1 row(s)", file=sys.stderr)
    if args.table:
        print(table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
