#!/usr/bin/env python3
"""Project LinkedIn normalized jobs into primitive, table-oriented fields."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

from parse_output import load_records, validate_normalized_job


FLAT_SCHEMA_VERSION = "nomad-agent-flat-job-v1"
ARRAY_FIELDS = frozenset(
    {
        "workArrangements", "workSchedules", "contractTypes", "seniorityLevels",
        "industries", "jobFunctions",
    }
)
NUMBER_FIELDS = frozenset({"salaryExact", "salaryMinimum", "salaryMaximum"})
BOOLEAN_FIELDS = frozenset({"directApply"})
REQUIRED_FLAT_FIELDS = frozenset(
    {
        "schemaVersion", "jobKey", "source", "identityExternalId", "jobUrl", "title",
        "companyName", "companySourceId", "companyUrl", "locationText", "countryCode",
        "city", "region", "workArrangements", "workSchedules", "contractTypes",
        "postedAt", "applicationDeadline", "applicationUrl", "applicationEmail",
        "directApply", "seniorityLevels", "industries", "jobFunctions", "salaryCurrency",
        "salaryExact", "salaryMinimum", "salaryMaximum", "salaryPeriod", "salaryRaw",
        "descriptionText", "llmStatus",
    }
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _array_json(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"expected array or null, got {type(value).__name__}")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _location_label(location: Mapping[str, Any]) -> str | None:
    raw = location.get("raw")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    parts = [location.get("city"), location.get("region"), location.get("countryName")]
    values = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
    return ", ".join(dict.fromkeys(values)) or None


def _locations_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("data.locations must be an array or null")
    labels = [_location_label(_mapping(location)) for location in value]
    return " | ".join(label for label in labels if label)


def validate_flat_job(value: Any, *, include_record_json: bool = False) -> Mapping[str, Any]:
    """Validate the generated record against flat-job-v1's closed primitive shape."""
    if not isinstance(value, Mapping):
        raise ValueError("flat job must be an object")
    expected = set(REQUIRED_FLAT_FIELDS)
    if include_record_json:
        expected.add("normalizedRecordJson")
    if set(value) != expected:
        raise ValueError(
            f"flat job keys mismatch; missing={sorted(expected - set(value))}, "
            f"extra={sorted(set(value) - expected)}"
        )
    if value["schemaVersion"] != FLAT_SCHEMA_VERSION:
        raise ValueError(f"schemaVersion must be {FLAT_SCHEMA_VERSION}")
    for field, item in value.items():
        if field in NUMBER_FIELDS:
            if item is not None and (
                type(item) is bool
                or not isinstance(item, (int, float))
                or (isinstance(item, float) and not math.isfinite(item))
            ):
                raise ValueError(f"{field} must be a finite number or null")
        elif field in BOOLEAN_FIELDS:
            if item is not None and type(item) is not bool:
                raise ValueError(f"{field} must be a boolean or null")
        elif item is not None and not isinstance(item, str):
            raise ValueError(f"{field} must be a string or null")
    for field in ("jobKey", "source"):
        if not value[field]:
            raise ValueError(f"{field} must be a non-empty string")
    for field in ARRAY_FIELDS:
        if value[field] is not None:
            try:
                decoded = json.loads(value[field])
            except json.JSONDecodeError as exc:
                raise ValueError(f"{field} must contain a JSON array") from exc
            if not isinstance(decoded, list):
                raise ValueError(f"{field} must contain a JSON array")
    if value["llmStatus"] not in {"not_requested", "completed", "failed"}:
        raise ValueError("llmStatus has an unsupported value")
    if include_record_json:
        try:
            normalized = json.loads(value["normalizedRecordJson"])
        except json.JSONDecodeError as exc:
            raise ValueError("normalizedRecordJson must contain valid JSON") from exc
        validate_normalized_job(normalized)
    return value


def flatten_job(item: Any, *, include_record_json: bool = False) -> dict[str, Any]:
    record = validate_normalized_job(item)
    identity = _mapping(record["identity"])
    data = _mapping(record["data"])
    company = _mapping(data.get("company"))
    classification = _mapping(data.get("classification"))
    employment = _mapping(data.get("employment"))
    application = _mapping(data.get("application"))
    seniority = _mapping(data.get("seniority"))
    compensation = _mapping(data.get("compensation"))
    llm = _mapping(record["llm"])
    raw = _mapping(record["raw"])
    locations = data.get("locations")
    first_location = _mapping(locations[0]) if isinstance(locations, list) and locations else {}

    source = identity.get("source")
    external_id = identity.get("externalId")
    job_url = identity.get("url")
    stable_part = external_id or job_url
    if not stable_part:
        raise ValueError("identity.externalId or identity.url is required for flat jobKey")

    flat = {
        "schemaVersion": FLAT_SCHEMA_VERSION,
        "jobKey": f"{source}:{stable_part}",
        "source": source,
        "identityExternalId": external_id,
        "jobUrl": job_url,
        "title": data.get("title"),
        "companyName": company.get("name"),
        "companySourceId": company.get("sourceId"),
        "companyUrl": company.get("url"),
        "locationText": _locations_text(locations),
        "countryCode": first_location.get("countryCode"),
        "city": first_location.get("city"),
        "region": first_location.get("region"),
        "workArrangements": _array_json(employment.get("workArrangements")),
        "workSchedules": _array_json(employment.get("workSchedules")),
        "contractTypes": _array_json(employment.get("contractTypes")),
        "postedAt": application.get("postedAt"),
        "applicationDeadline": application.get("deadline"),
        "applicationUrl": application.get("url"),
        "applicationEmail": application.get("email"),
        "directApply": application.get("directApply"),
        "seniorityLevels": _array_json(seniority.get("levels")),
        "industries": _array_json(classification.get("industries")),
        "jobFunctions": _array_json(classification.get("jobFunctions")),
        "salaryCurrency": compensation.get("currency"),
        "salaryExact": compensation.get("exact"),
        "salaryMinimum": compensation.get("minimum"),
        "salaryMaximum": compensation.get("maximum"),
        "salaryPeriod": compensation.get("period"),
        "salaryRaw": compensation.get("raw"),
        "descriptionText": raw.get("description"),
        "llmStatus": llm.get("status"),
    }
    if include_record_json:
        flat["normalizedRecordJson"] = json.dumps(
            record, ensure_ascii=False, separators=(",", ":")
        )
    return dict(validate_flat_job(flat, include_record_json=include_record_json))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="JSON/JSONL file; omit for stdin")
    parser.add_argument("--output", type=Path, help="Write JSON here; default stdout")
    parser.add_argument("--include-record-json", action="store_true")
    args = parser.parse_args()

    flattened = [
        flatten_job(item, include_record_json=args.include_record_json)
        for item in load_records(args.input)
    ]
    rendered = json.dumps(flattened, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
