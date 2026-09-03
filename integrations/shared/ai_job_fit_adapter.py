"""Closed fit-row validation and Google-Sheets-safe projection."""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence


SOURCE_RECORD_JSON_MAX_CHARS = 48_000
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
STATUSES = {
    "scored",
    "static_drop",
    "static_hold",
    "forward_cap_hold",
    "ai_failed",
}
EXPECTED_KEYS = {
    "schemaVersion",
    "matchKey",
    "evaluationKey",
    "jobKey",
    "candidateHash",
    "candidateSnapshotHash",
    "evaluatedAt",
    "source",
    "externalId",
    "url",
    "title",
    "company",
    "location",
    "postedAt",
    "fitScore",
    "deliveryScore",
    "recommendation",
    "evaluationStatus",
    "why",
    "gapSummary",
    "blockingGates",
    "scoreAdjustedForGates",
    "gates",
    "staticDecision",
    "scoring",
    "job",
}
COLUMNS = (
    "schemaVersion",
    "matchKey",
    "evaluationKey",
    "jobKey",
    "candidateHash",
    "candidateSnapshotHash",
    "evaluatedAt",
    "fitScore",
    "deliveryScore",
    "recommendation",
    "evaluationStatus",
    "title",
    "company",
    "location",
    "url",
    "blockingGatesJson",
    "why",
    "gapSummary",
    "sourceRunId",
    "sourceBuild",
    "evaluationJson",
)


class ContractError(ValueError):
    """A dataset row is not the declared fit output contract."""


def _integer_or_none(value: Any, *, field: str, minimum: int, maximum: int) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{field} must be an integer or null")
    if not minimum <= value <= maximum:
        raise ContractError(f"{field} must be {minimum} through {maximum}")


def _bounded_json(row: Mapping[str, Any]) -> str:
    rendered = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(rendered) <= SOURCE_RECORD_JSON_MAX_CHARS:
        return rendered
    return json.dumps(
        {
            "_truncated": True,
            "originalChars": len(rendered),
            "schemaVersion": row.get("schemaVersion"),
            "matchKey": row.get("matchKey"),
            "evaluationKey": row.get("evaluationKey"),
            "jobKey": row.get("jobKey"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def validate_and_project(row: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(row, Mapping):
        raise ContractError("fit row must be an object")
    if set(row) != EXPECTED_KEYS:
        raise ContractError("fit row must be exact nomad-ai-job-fit-v1")
    if row.get("schemaVersion") != "nomad-ai-job-fit-v1":
        raise ContractError("unexpected fit schemaVersion")
    for field in (
        "matchKey",
        "evaluationKey",
        "candidateHash",
        "candidateSnapshotHash",
    ):
        if not isinstance(row.get(field), str) or not HASH_RE.fullmatch(row[field]):
            raise ContractError(f"{field} must be a lowercase SHA-256 hash")
    if not isinstance(row.get("jobKey"), str) or ":" not in row["jobKey"]:
        raise ContractError("jobKey must preserve source identity")
    status = row.get("evaluationStatus")
    if status not in STATUSES:
        raise ContractError("unknown evaluationStatus")
    _integer_or_none(row.get("fitScore"), field="fitScore", minimum=0, maximum=100)
    _integer_or_none(
        row.get("deliveryScore"), field="deliveryScore", minimum=0, maximum=5
    )
    if not isinstance(row.get("blockingGates"), list):
        raise ContractError("blockingGates must be an array")
    job = row.get("job")
    if not isinstance(job, Mapping) or job.get("schemaVersion") != "nomad-agent-job-v1":
        raise ContractError("job must be a canonical nomad-agent-job-v1 record")
    scoring = row.get("scoring")
    if not isinstance(scoring, Mapping) or scoring.get("algorithm") != "scoring-v3":
        raise ContractError("scoring receipt must identify scoring-v3")
    if not isinstance(scoring.get("sourceProvenance"), Mapping):
        raise ContractError("scoring receipt must preserve sourceProvenance")

    if status == "scored" and (
        row.get("fitScore") is None or row.get("deliveryScore") is None
    ):
        raise ContractError("scored row requires both scores")
    if status == "static_drop" and (
        row.get("fitScore") != 0 or row.get("deliveryScore") != 0
    ):
        raise ContractError("static_drop must preserve zero scores")
    if status in {"static_hold", "forward_cap_hold"} and (
        row.get("fitScore") is not None or row.get("deliveryScore") is not None
    ):
        raise ContractError("held rows must preserve unknown scores")
    if status == "ai_failed":
        return None

    provenance = scoring["sourceProvenance"]
    source_build = provenance.get("buildNumber") or provenance.get("buildId")
    return {
        "schemaVersion": "nomad-ai-job-fit-destination-v1",
        "matchKey": row["matchKey"],
        "evaluationKey": row["evaluationKey"],
        "jobKey": row["jobKey"],
        "candidateHash": row["candidateHash"],
        "candidateSnapshotHash": row["candidateSnapshotHash"],
        "evaluatedAt": row.get("evaluatedAt"),
        "fitScore": row.get("fitScore"),
        "deliveryScore": row.get("deliveryScore"),
        "recommendation": row.get("recommendation"),
        "evaluationStatus": status,
        "title": row.get("title"),
        "company": row.get("company"),
        "location": row.get("location"),
        "url": row.get("url"),
        "blockingGatesJson": json.dumps(row["blockingGates"], ensure_ascii=False),
        "why": row.get("why"),
        "gapSummary": row.get("gapSummary"),
        "sourceRunId": provenance.get("actorRunId"),
        "sourceBuild": source_build,
        "evaluationJson": _bounded_json(row),
    }


def project_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        item = validate_and_project(row)
        if item is None:
            continue
        if item["matchKey"] in seen:
            raise ContractError(f"duplicate matchKey {item['matchKey']}")
        seen.add(item["matchKey"])
        projected.append(item)
    return projected


def upsert_rows(
    destination: dict[str, dict[str, Any]], rows: Sequence[Mapping[str, Any]]
) -> tuple[int, int]:
    inserted = updated = 0
    for row in project_rows(rows):
        key = row["matchKey"]
        if key in destination:
            updated += 1
        else:
            inserted += 1
        destination[key] = row
    return inserted, updated
