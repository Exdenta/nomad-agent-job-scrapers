#!/usr/bin/env python3
"""Validate the closed LinkedIn nomad-agent-job-v1 wire contract."""

from __future__ import annotations

import datetime
import math
import re
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit


ROOT_KEYS = frozenset({"schemaVersion", "identity", "data", "custom", "llm", "raw"})
LLM_STATUSES = frozenset({"not_requested", "completed", "failed"})
WORK_ARRANGEMENTS = frozenset({"remote", "hybrid", "onsite"})
SENIORITY_LEVELS = frozenset(
    {
        "intern", "entry", "junior", "mid", "senior", "staff", "lead",
        "principal", "manager", "director", "executive", "R1", "R2", "R3", "R4",
    }
)
AVAILABILITY_STATUSES = frozenset(
    {"observed_available", "observed_unavailable", "unknown"}
)
AVAILABILITY_EVIDENCE_KINDS = frozenset(
    {
        "search_card_present", "detail_http_status", "detail_jobposting_markup",
        "detail_unavailable_marker", "source_label",
    }
)
COUNTRY_CODE_RE = re.compile(r"^[A-Z]{2}$")
ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
LLM_PATH_RE = re.compile(
    r"^data(?:\.[A-Za-z][A-Za-z0-9]*|\[(?:0|[1-9][0-9]*)\])+$"
)
LLM_PATH_TOKEN_RE = re.compile(
    r"\.([A-Za-z][A-Za-z0-9]*)|\[(0|[1-9][0-9]*)\]"
)
MISSING = object()


class ContractValidationError(ValueError):
    """Raised when a value does not match the public wire contract."""


def _object(value: Any, path: str, keys: set[str] | frozenset[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{path} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ContractValidationError(f"{path} keys must be strings")
    actual = frozenset(value)
    expected = frozenset(keys)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ContractValidationError(
            f"{path} has missing keys {missing!r} and extra keys {extra!r}"
        )
    return value


def _string(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        suffix = " or null" if nullable else ""
        raise ContractValidationError(f"{path} must be a non-empty string{suffix}")
    return value


def _boolean(value: Any, path: str, *, nullable: bool = False) -> bool | None:
    if value is None and nullable:
        return None
    if type(value) is not bool:
        suffix = " or null" if nullable else ""
        raise ContractValidationError(f"{path} must be a boolean{suffix}")
    return value


def _number(
    value: Any,
    path: str,
    *,
    nullable: bool = False,
    integer: bool = False,
    minimum: float | None = None,
    maximum: float | None = None,
) -> int | float | None:
    if value is None and nullable:
        return None
    valid = type(value) is int if integer else isinstance(value, (int, float)) and type(value) is not bool
    if not valid or (isinstance(value, float) and not math.isfinite(value)):
        kind = "integer" if integer else "finite number"
        suffix = " or null" if nullable else ""
        raise ContractValidationError(f"{path} must be a {kind}{suffix}")
    if minimum is not None and value < minimum:
        raise ContractValidationError(f"{path} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ContractValidationError(f"{path} must be at most {maximum}")
    return value


def _list(
    value: Any,
    path: str,
    item_validator: Callable[[Any, str], None],
    *,
    nullable: bool = False,
) -> list[Any] | None:
    if value is None and nullable:
        return None
    if not isinstance(value, list):
        suffix = " or null" if nullable else ""
        raise ContractValidationError(f"{path} must be an array{suffix}")
    for index, item in enumerate(value):
        item_validator(item, f"{path}[{index}]")
    return value


def _string_item(value: Any, path: str) -> None:
    _string(value, path)


def _enum_item(allowed: frozenset[str]) -> Callable[[Any, str], None]:
    def validate(value: Any, path: str) -> None:
        _string(value, path)
        if value not in allowed:
            raise ContractValidationError(f"{path} must be one of {sorted(allowed)!r}")

    return validate


def _iso_date(value: Any, path: str) -> None:
    text = _string(value, path, nullable=True)
    if text is None:
        return
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        datetime.datetime.fromisoformat(normalized)
    except ValueError:
        try:
            datetime.date.fromisoformat(text)
        except ValueError as exc:
            raise ContractValidationError(f"{path} must be an ISO 8601 date or datetime") from exc


def _iso_datetime(value: Any, path: str, *, nullable: bool = False) -> None:
    text = _string(value, path, nullable=nullable)
    if text is None:
        return
    if not ISO_DATETIME_RE.match(text):
        raise ContractValidationError(f"{path} must be an ISO 8601 datetime")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractValidationError(f"{path} must be an ISO 8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ContractValidationError(f"{path} must include a timezone")


def _company(value: Any, path: str) -> None:
    item = _object(value, path, {"name", "sourceId", "department", "url", "logoUrl"})
    for field in item:
        _string(item[field], f"{path}.{field}", nullable=True)


def _classification(value: Any, path: str) -> None:
    item = _object(value, path, {"industries", "jobFunctions"})
    for field in item:
        _list(item[field], f"{path}.{field}", _string_item, nullable=True)


def _location(value: Any, path: str) -> None:
    keys = {
        "raw", "countryName", "countryCode", "city", "region", "postalCode",
        "streetAddress", "facilityName", "positionsAvailable", "latitude", "longitude",
    }
    item = _object(value, path, keys)
    for field in keys - {"positionsAvailable", "latitude", "longitude"}:
        _string(item[field], f"{path}.{field}", nullable=True)
    code = item["countryCode"]
    if code is not None and not COUNTRY_CODE_RE.fullmatch(code):
        raise ContractValidationError(f"{path}.countryCode must be an uppercase ISO alpha-2 code")
    _number(item["positionsAvailable"], f"{path}.positionsAvailable", nullable=True, integer=True, minimum=0)
    _number(item["latitude"], f"{path}.latitude", nullable=True, minimum=-90, maximum=90)
    _number(item["longitude"], f"{path}.longitude", nullable=True, minimum=-180, maximum=180)


def _employment(value: Any, path: str) -> None:
    keys = {
        "workArrangements", "applicantLocationRequirements", "workSchedules",
        "contractTypes", "durationMonths", "hoursPerWeek", "hoursPerWeekRaw",
        "startDate", "startDateRaw",
    }
    item = _object(value, path, keys)
    _list(item["workArrangements"], f"{path}.workArrangements", _enum_item(WORK_ARRANGEMENTS), nullable=True)
    for field in ("applicantLocationRequirements", "workSchedules", "contractTypes"):
        _list(item[field], f"{path}.{field}", _string_item, nullable=True)
    for field in ("durationMonths", "hoursPerWeek"):
        _number(item[field], f"{path}.{field}", nullable=True, minimum=0)
    _string(item["hoursPerWeekRaw"], f"{path}.hoursPerWeekRaw", nullable=True)
    _iso_date(item["startDate"], f"{path}.startDate")
    _string(item["startDateRaw"], f"{path}.startDateRaw", nullable=True)


def _contact_address(value: Any, path: str) -> None:
    item = _object(
        value, path,
        {"raw", "countryName", "countryCode", "city", "region", "postalCode", "streetAddress"},
    )
    for field in item:
        _string(item[field], f"{path}.{field}", nullable=True)
    code = item["countryCode"]
    if code is not None and not COUNTRY_CODE_RE.fullmatch(code):
        raise ContractValidationError(f"{path}.countryCode must be an uppercase ISO alpha-2 code")


def _hiring_contact(value: Any, path: str) -> None:
    keys = {"name", "title", "organization", "url", "photoUrl", "email", "address"}
    item = _object(value, path, keys)
    for field in keys - {"address"}:
        _string(item[field], f"{path}.{field}", nullable=True)
    if item["address"] is not None:
        _contact_address(item["address"], f"{path}.address")
    if all(item[field] is None for field in keys):
        raise ContractValidationError(f"{path} must contain at least one contact fact")
    if item["photoUrl"] is not None:
        parsed_url = urlsplit(item["photoUrl"])
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ContractValidationError(
                f"{path}.photoUrl must be an absolute HTTP(S) URL"
            )


def _applicant_snapshot(value: Any, path: str) -> None:
    item = _object(value, path, {"count", "raw", "capturedAt"})
    _number(item["count"], f"{path}.count", nullable=True, integer=True, minimum=0)
    _string(item["raw"], f"{path}.raw")
    _iso_datetime(item["capturedAt"], f"{path}.capturedAt")


def _availability_evidence(value: Any, path: str) -> None:
    item = _object(value, path, {"kind", "value"})
    _string(item["kind"], f"{path}.kind")
    if item["kind"] not in AVAILABILITY_EVIDENCE_KINDS:
        raise ContractValidationError(f"{path}.kind has an unsupported value")
    _string(item["value"], f"{path}.value", nullable=True)


def _availability(value: Any, path: str) -> None:
    item = _object(value, path, {"status", "evidence", "observedAt"})
    _string(item["status"], f"{path}.status")
    if item["status"] not in AVAILABILITY_STATUSES:
        raise ContractValidationError(f"{path}.status has an unsupported value")
    evidence = _list(item["evidence"], f"{path}.evidence", _availability_evidence)
    if not evidence:
        raise ContractValidationError(f"{path}.evidence must not be empty")
    fingerprints = [(entry["kind"], entry["value"]) for entry in evidence]
    if len(fingerprints) != len(set(fingerprints)):
        raise ContractValidationError(f"{path}.evidence must contain unique items")
    _iso_datetime(item["observedAt"], f"{path}.observedAt")


def _application(value: Any, path: str) -> None:
    keys = {
        "postedAt", "deadline", "referenceNumber", "referenceNumberIssuer",
        "applicantSnapshot", "url", "email", "directApply", "applyMethodRaw",
        "availability", "hiringContacts", "eligibilityCriteria", "selectionProcess",
    }
    item = _object(value, path, keys)
    _iso_date(item["postedAt"], f"{path}.postedAt")
    _iso_date(item["deadline"], f"{path}.deadline")
    for field in (
        "referenceNumber", "referenceNumberIssuer", "url", "email", "applyMethodRaw",
        "eligibilityCriteria", "selectionProcess",
    ):
        _string(item[field], f"{path}.{field}", nullable=True)
    _boolean(item["directApply"], f"{path}.directApply", nullable=True)
    if item["applicantSnapshot"] is not None:
        _applicant_snapshot(item["applicantSnapshot"], f"{path}.applicantSnapshot")
    if item["availability"] is not None:
        _availability(item["availability"], f"{path}.availability")
    _list(item["hiringContacts"], f"{path}.hiringContacts", _hiring_contact, nullable=True)


def _seniority(value: Any, path: str) -> None:
    item = _object(value, path, {"raw", "levels"})
    _list(item["raw"], f"{path}.raw", _string_item, nullable=True)
    _list(item["levels"], f"{path}.levels", _enum_item(SENIORITY_LEVELS), nullable=True)


def _education(value: Any, path: str) -> None:
    item = _object(value, path, {"level", "field", "yearsRequired", "preferred"})
    _string(item["level"], f"{path}.level", nullable=True)
    _string(item["field"], f"{path}.field", nullable=True)
    _number(item["yearsRequired"], f"{path}.yearsRequired", nullable=True, minimum=0)
    _boolean(item["preferred"], f"{path}.preferred", nullable=True)
    if item["level"] is None and item["field"] is None:
        raise ContractValidationError(f"{path} must identify a level or field")


def _experience(value: Any, path: str) -> None:
    item = _object(value, path, {"field", "minimumYears", "maximumYears", "raw"})
    _string(item["field"], f"{path}.field", nullable=True)
    minimum = _number(item["minimumYears"], f"{path}.minimumYears", nullable=True, minimum=0)
    maximum = _number(item["maximumYears"], f"{path}.maximumYears", nullable=True, minimum=0)
    _string(item["raw"], f"{path}.raw", nullable=True)
    if all(item[field] is None for field in item):
        raise ContractValidationError(f"{path} must contain at least one experience fact")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ContractValidationError(f"{path}.minimumYears cannot exceed maximumYears")


def _language(value: Any, path: str) -> None:
    item = _object(value, path, {"language", "level", "required"})
    _string(item["language"], f"{path}.language")
    _string(item["level"], f"{path}.level", nullable=True)
    _boolean(item["required"], f"{path}.required", nullable=True)


def _skill(value: Any, path: str) -> None:
    item = _object(value, path, {"name", "yearsRequired"})
    _string(item["name"], f"{path}.name")
    _number(item["yearsRequired"], f"{path}.yearsRequired", nullable=True, minimum=0)


def _requirements(value: Any, path: str) -> None:
    keys = {
        "education", "experience", "languages", "requiredSkills", "preferredSkills",
        "certifications", "skillsQualifications", "specificRequirements",
    }
    item = _object(value, path, keys)
    _list(item["education"], f"{path}.education", _education, nullable=True)
    _list(item["experience"], f"{path}.experience", _experience, nullable=True)
    _list(item["languages"], f"{path}.languages", _language, nullable=True)
    _list(item["requiredSkills"], f"{path}.requiredSkills", _skill, nullable=True)
    _list(item["preferredSkills"], f"{path}.preferredSkills", _skill, nullable=True)
    _list(item["certifications"], f"{path}.certifications", _string_item, nullable=True)
    _string(item["skillsQualifications"], f"{path}.skillsQualifications", nullable=True)
    _string(item["specificRequirements"], f"{path}.specificRequirements", nullable=True)


def _compensation(value: Any, path: str) -> None:
    item = _object(value, path, {"currency", "exact", "minimum", "maximum", "period", "raw"})
    _string(item["currency"], f"{path}.currency", nullable=True)
    exact = _number(item["exact"], f"{path}.exact", nullable=True, minimum=0)
    minimum = _number(item["minimum"], f"{path}.minimum", nullable=True, minimum=0)
    maximum = _number(item["maximum"], f"{path}.maximum", nullable=True, minimum=0)
    _string(item["period"], f"{path}.period", nullable=True)
    _string(item["raw"], f"{path}.raw", nullable=True)
    if exact is not None and (minimum is not None or maximum is not None):
        raise ContractValidationError(f"{path}.exact is mutually exclusive with minimum/maximum")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ContractValidationError(f"{path}.minimum cannot exceed maximum")


def _llm_path_tokens(path: str) -> tuple[str | int, ...]:
    if not LLM_PATH_RE.fullmatch(path):
        raise ContractValidationError(f"invalid LLM field path: {path!r}")
    return tuple(
        field if field else int(index)
        for field, index in LLM_PATH_TOKEN_RE.findall(path[4:])
    )


def _lookup(root: Any, tokens: tuple[str | int, ...]) -> Any:
    value = root
    for token in tokens:
        if isinstance(token, str):
            if not isinstance(value, Mapping) or token not in value:
                return MISSING
            value = value[token]
        else:
            if not isinstance(value, list) or token >= len(value):
                return MISSING
            value = value[token]
    return value


def _llm(value: Any, path: str, data: Mapping[str, Any]) -> None:
    keys = {"status", "requestedFields", "filledFields", "provider", "model", "promptVersion", "completedAt"}
    item = _object(value, path, keys)
    _string(item["status"], f"{path}.status")
    if item["status"] not in LLM_STATUSES:
        raise ContractValidationError(f"{path}.status must be one of {sorted(LLM_STATUSES)!r}")
    requested = _list(item["requestedFields"], f"{path}.requestedFields", _string_item)
    filled = _list(item["filledFields"], f"{path}.filledFields", _string_item)
    if len(requested) != len(set(requested)):
        raise ContractValidationError(f"{path}.requestedFields must contain unique paths")
    parsed: list[tuple[str, tuple[str | int, ...]]] = []
    for field_path in requested:
        tokens = _llm_path_tokens(field_path)
        for other_path, other_tokens in parsed:
            if tokens[: len(other_tokens)] == other_tokens or other_tokens[: len(tokens)] == tokens:
                raise ContractValidationError(
                    f"overlapping LLM field paths: {other_path!r} and {field_path!r}"
                )
        if _lookup(data, tokens) is MISSING:
            raise ContractValidationError(f"LLM field path does not exist: {field_path!r}")
        parsed.append((field_path, tokens))
    if len(filled) != len(set(filled)) or any(field not in requested for field in filled):
        raise ContractValidationError(f"{path}.filledFields must be a unique subset of requestedFields")
    if [field for field in requested if field in filled] != filled:
        raise ContractValidationError(f"{path}.filledFields must preserve requestedFields order")
    for field_path in filled:
        if _lookup(data, _llm_path_tokens(field_path)) in (MISSING, None):
            raise ContractValidationError(f"filled LLM field is null or missing: {field_path!r}")
    if item["status"] != "completed" and filled:
        raise ContractValidationError(f"{path}.filledFields requires completed status")
    if item["status"] == "not_requested" and requested:
        raise ContractValidationError(f"{path}.requestedFields must be empty when not_requested")
    for field in ("provider", "model", "promptVersion"):
        _string(item[field], f"{path}.{field}", nullable=True)
    _iso_datetime(item["completedAt"], f"{path}.completedAt", nullable=True)


def validate_linkedin_job(value: Any) -> Mapping[str, Any]:
    """Return the record after validating every v1 field and nested key."""
    record = _object(value, "item", ROOT_KEYS)
    if record["schemaVersion"] != "nomad-agent-job-v1":
        raise ContractValidationError("schemaVersion must be nomad-agent-job-v1")

    identity = _object(record["identity"], "identity", {"source", "externalId", "url"})
    if identity["source"] != "linkedin":
        raise ContractValidationError("identity.source must be linkedin")
    _string(identity["externalId"], "identity.externalId", nullable=True)
    _string(identity["url"], "identity.url", nullable=True)

    data_keys = {
        "title", "company", "classification", "domains", "domainsRaw", "locations",
        "employment", "application", "seniority", "requirements", "benefits", "funding",
        "compensation", "constraints",
    }
    data = _object(record["data"], "data", data_keys)
    _string(data["title"], "data.title", nullable=True)
    _company(data["company"], "data.company")
    _classification(data["classification"], "data.classification")
    _list(data["domains"], "data.domains", _string_item, nullable=True)
    _list(data["domainsRaw"], "data.domainsRaw", _string_item, nullable=True)
    _list(data["locations"], "data.locations", _location, nullable=True)
    _employment(data["employment"], "data.employment")
    _application(data["application"], "data.application")
    _seniority(data["seniority"], "data.seniority")
    _requirements(data["requirements"], "data.requirements")
    _string(data["benefits"], "data.benefits", nullable=True)
    funding = _object(data["funding"], "data.funding", {"programme"})
    _string(funding["programme"], "data.funding.programme", nullable=True)
    _compensation(data["compensation"], "data.compensation")
    constraints = _object(
        data["constraints"], "data.constraints",
        {"visaSponsorship", "workAuthorization", "securityClearance", "locationPreference"},
    )
    _boolean(constraints["visaSponsorship"], "data.constraints.visaSponsorship", nullable=True)
    for field in ("workAuthorization", "securityClearance", "locationPreference"):
        _string(constraints[field], f"data.constraints.{field}", nullable=True)

    if record["custom"] is not None:
        raise ContractValidationError("custom must be null for LinkedIn")
    _llm(record["llm"], "llm", data)
    if record["raw"] is not None:
        raw = _object(record["raw"], "raw", {"description", "descriptionHtml"})
        _string(raw["description"], "raw.description", nullable=True)
        _string(raw["descriptionHtml"], "raw.descriptionHtml", nullable=True)
    return record
