#!/usr/bin/env python3
"""Validate LinkedIn nomad-agent-job-v1 output without losing the source record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from validate_contract import ContractValidationError, validate_linkedin_job


class OutputContractError(ValueError):
    """Raised when an Actor item does not match the expected envelope."""


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OutputContractError(f"{path} must be an object")
    return value


def validate_normalized_job(item: Any) -> Mapping[str, Any]:
    try:
        return validate_linkedin_job(item)
    except ContractValidationError as exc:
        raise OutputContractError(str(exc)) from exc


def parse_linkedin_output(item: Any) -> dict[str, Any]:
    record = validate_normalized_job(item)
    identity = _mapping(record["identity"], "identity")
    data = _mapping(record["data"], "data")
    company = _mapping(data["company"], "data.company")
    application = _mapping(data["application"], "data.application")
    llm = _mapping(record["llm"], "llm")
    raw = record["raw"]
    source = identity.get("source")
    external_id = identity.get("externalId")
    posting_url = identity.get("url")
    stable_part = external_id or posting_url

    return {
        "id": external_id,
        "jobKey": f"{source}:{stable_part}" if stable_part else None,
        "source": source,
        "postingUrl": posting_url,
        "title": data.get("title"),
        "company": company.get("name"),
        "locations": data.get("locations"),
        "postedAt": application.get("postedAt"),
        "applicationUrl": application.get("url"),
        "description": raw.get("description") if isinstance(raw, Mapping) else None,
        "llmStatus": llm.get("status"),
        "normalized": record,
    }


def parse_linkedin_outputs(items: Iterable[Any]) -> list[dict[str, Any]]:
    return [parse_linkedin_output(item) for item in items]


def load_records(path: Path | None) -> list[Any]:
    text = path.read_text(encoding="utf-8") if path else sys.stdin.read()
    if not text.strip():
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(value, list):
        return value
    if isinstance(value, Mapping):
        return [value]
    raise OutputContractError("input must be a JSON object, JSON array, or JSON Lines")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="JSON/JSONL file; omit for stdin")
    parser.add_argument("--output", type=Path, help="Write JSON here; default stdout")
    args = parser.parse_args()

    parsed = parse_linkedin_outputs(load_records(args.input))
    rendered = json.dumps(parsed, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
