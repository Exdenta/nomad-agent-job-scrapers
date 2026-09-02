#!/usr/bin/env python3
"""Validate and score final Actor records against benchmark v1."""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable


SCORER_VERSION = "nomad-agent-enrichment-scorer-v1"
BENCHMARK_SCHEMA = "nomad-agent-enrichment-benchmark-v1"
SUBMISSION_SCHEMA = "nomad-agent-enrichment-submission-v1"
SOURCES = ("linkedin", "euraxess")
EXPECTED_STATES = {"present", "absent", "ambiguous"}
MATCHERS = {"exact", "unordered_array"}
PATH_RE = re.compile(r"^(?:data|identity)(?:\.[A-Za-z0-9_]+)+$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
BUILD_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
MISSING = object()


class ValidationError(ValueError):
    pass


def _fail(message: str) -> None:
    raise ValidationError(message)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"cannot read valid JSON from {path}: {exc}")
    if not isinstance(value, dict):
        _fail(f"{path} must contain one JSON object")
    return value


def _path_value(value: Any, path: str, default: Any = MISSING) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return default
    return current


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _matches(actual: Any, accepted: list[Any], matcher: str) -> bool:
    if matcher == "exact":
        return any(actual == candidate for candidate in accepted)
    if matcher == "unordered_array":
        if not isinstance(actual, list):
            return False
        actual_items = sorted(_canonical(item) for item in actual)
        return any(
            isinstance(candidate, list)
            and actual_items == sorted(_canonical(item) for item in candidate)
            for candidate in accepted
        )
    _fail(f"unsupported matcher: {matcher}")


def _new_counts() -> Counter[str]:
    return Counter({
        "truePositive": 0,
        "trueNegative": 0,
        "falsePositive": 0,
        "falseNegative": 0,
        "wrongValue": 0,
        "unsupportedFill": 0,
        "ambiguousExcluded": 0,
        "scored": 0,
        "exact": 0,
    })


def _update_counts(counts: Counter[str], expected: str, actual: Any, matches: bool) -> None:
    if expected == "ambiguous":
        counts["ambiguousExcluded"] += 1
        return
    counts["scored"] += 1
    if expected == "present":
        if matches:
            counts["truePositive"] += 1
            counts["exact"] += 1
        elif actual is MISSING or actual is None:
            counts["falseNegative"] += 1
        else:
            counts["wrongValue"] += 1
            counts["falsePositive"] += 1
            counts["falseNegative"] += 1
        return
    if actual is MISSING or actual is None:
        counts["trueNegative"] += 1
        counts["exact"] += 1
    else:
        counts["falsePositive"] += 1
        counts["unsupportedFill"] += 1


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 2) if denominator else None


def _wilson(successes: int, total: int) -> list[float] | None:
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [round(100 * max(0.0, centre - margin), 2), round(100 * min(1.0, centre + margin), 2)]


def _metrics(counts: Counter[str]) -> dict[str, Any]:
    tp = counts["truePositive"]
    tn = counts["trueNegative"]
    fp = counts["falsePositive"]
    fn = counts["falseNegative"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    absent_total = tn + counts["unsupportedFill"]
    result = dict(sorted(counts.items()))
    result.update({
        "precisionPct": round(100 * precision, 2) if precision is not None else None,
        "recallPct": round(100 * recall, 2) if recall is not None else None,
        "f1Pct": round(100 * f1, 2) if f1 is not None else None,
        "exactCaseFieldAccuracyPct": _ratio(counts["exact"], counts["scored"]),
        "specificityPct": _ratio(tn, absent_total),
        "unsupportedFillRatePct": _ratio(counts["unsupportedFill"], absent_total),
        "recallWilson95Pct": _wilson(tp, tp + fn),
        "specificityWilson95Pct": _wilson(tn, absent_total),
        "exactAccuracyWilson95Pct": _wilson(counts["exact"], counts["scored"]),
    })
    return result


def _char_ngrams(text: str, order: int) -> Counter[str]:
    normalized = " ".join(text.casefold().split())
    return Counter(normalized[index:index + order] for index in range(max(0, len(normalized) - order + 1)))


def _chrf2(candidate: str, reference: str, max_order: int = 6) -> float:
    scores: list[float] = []
    beta2 = 4.0
    for order in range(1, max_order + 1):
        predicted = _char_ngrams(candidate, order)
        expected = _char_ngrams(reference, order)
        overlap = sum((predicted & expected).values())
        precision = overlap / sum(predicted.values()) if predicted else 0.0
        recall = overlap / sum(expected.values()) if expected else 0.0
        score = (
            (1 + beta2) * precision * recall / (beta2 * precision + recall)
            if precision or recall
            else 0.0
        )
        scores.append(score)
    return round(100 * sum(scores) / len(scores), 2)


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{context} must be an object")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{context} must be an array")
    return value


def _validate_record_shape(value: Any, context: str) -> dict[str, Any]:
    record = _require_object(value, context)
    required_roots = {"schemaVersion", "identity", "data", "custom", "llm", "raw"}
    if set(record) != required_roots:
        _fail(f"{context} must contain exactly the six nomad-agent-job-v1 roots")
    if record.get("schemaVersion") != "nomad-agent-job-v1":
        _fail(f"{context}.schemaVersion must be nomad-agent-job-v1")
    for root in ("identity", "data", "llm", "raw"):
        if not isinstance(record.get(root), dict):
            _fail(f"{context}.{root} must be an object")
    if record.get("custom") is not None and not isinstance(record.get("custom"), dict):
        _fail(f"{context}.custom must be an object or null")
    return record


@lru_cache(maxsize=2)
def _contract_validator(source: str):
    root = Path(__file__).resolve().parents[2]
    path = (
        root
        / ".agents"
        / "skills"
        / f"{source}-enrich-translate-normalize-scraper"
        / "scripts"
        / "validate_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        f"benchmark_{source}_contract_validator", path
    )
    if spec is None or spec.loader is None:
        _fail(f"cannot load the public {source} contract validator from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    function = getattr(module, f"validate_{source}_job", None)
    if not callable(function):
        _fail(f"public {source} contract validator has no callable entry point")
    return function


def _validate_closed_contract(record: dict[str, Any], source: str, context: str) -> None:
    try:
        _contract_validator(source)(record)
    except Exception as exc:
        _fail(f"{context} violates the closed {source} output contract: {exc}")


def _validate_review(value: Any, context: str, *, public_release: bool) -> dict[str, Any]:
    review = _require_object(value, context)
    quality = review.get("labelQuality")
    reviewers = review.get("independentHumanReviewers")
    adjudicated = review.get("adjudicated")
    if quality not in {"draft", "silver_consensus", "gold_human_verified"}:
        _fail(f"{context}.labelQuality is invalid")
    if isinstance(reviewers, bool) or not isinstance(reviewers, int) or reviewers < 0:
        _fail(f"{context}.independentHumanReviewers must be a non-negative integer")
    if type(adjudicated) is not bool:
        _fail(f"{context}.adjudicated must be a boolean")
    if public_release and (
        quality != "gold_human_verified" or reviewers < 2 or adjudicated is not True
    ):
        _fail(f"{context} requires independent human gold review")
    return review


def validate_benchmark(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schemaVersion") != BENCHMARK_SCHEMA:
        _fail("unexpected benchmark schemaVersion")
    benchmark_id = value.get("benchmarkId")
    if not isinstance(benchmark_id, str) or not benchmark_id:
        _fail("benchmarkId must be nonempty text")
    status = value.get("status")
    if status not in {"draft", "public_release"}:
        _fail("benchmark status must be draft or public_release")
    supported = _require_list(value.get("supportedEnrichmentPaths"), "supportedEnrichmentPaths")
    translation_paths = _require_list(value.get("translationPaths"), "translationPaths")
    for context, paths in (("supportedEnrichmentPaths", supported), ("translationPaths", translation_paths)):
        if len(paths) != len(set(paths)) or any(not isinstance(path, str) or not path.startswith("data.") for path in paths):
            _fail(f"{context} must contain unique data.* paths")
    if not supported:
        _fail("supportedEnrichmentPaths must not be empty")

    cases = _require_list(value.get("cases"), "cases")
    if not cases:
        _fail("cases must not be empty")
    seen_case_ids: set[str] = set()
    for index, raw_case in enumerate(cases):
        case = _require_object(raw_case, f"cases[{index}]")
        case_id = case.get("caseId")
        if not isinstance(case_id, str) or not case_id or case_id in seen_case_ids:
            _fail(f"cases[{index}].caseId must be unique nonempty text")
        seen_case_ids.add(case_id)
        source = case.get("source")
        if source not in SOURCES:
            _fail(f"{case_id}: source must be linkedin or euraxess")
        if case.get("split") not in {"development", "test"}:
            _fail(f"{case_id}: split must be development or test")
        document = _require_object(case.get("document"), f"{case_id}.document")
        text = document.get("text")
        digest = document.get("textSha256")
        if not isinstance(text, str) or not text:
            _fail(f"{case_id}: document text must be nonempty")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest) or _sha256_text(text) != digest:
            _fail(f"{case_id}: document textSha256 mismatch")
        if document.get("redistributable") is not True or not isinstance(document.get("redistributionBasis"), str):
            _fail(f"{case_id}: public cases require a redistribution basis")
        static = _validate_record_shape(case.get("staticRecord"), f"{case_id}.staticRecord")
        if _path_value(static, "identity.source") != source:
            _fail(f"{case_id}: staticRecord identity.source does not match case source")
        if status == "public_release":
            _validate_closed_contract(static, source, f"{case_id}.staticRecord")
        protected = _require_list(case.get("staticProtectedPaths"), f"{case_id}.staticProtectedPaths")
        if len(protected) != len(set(protected)):
            _fail(f"{case_id}: staticProtectedPaths must be unique")
        for path in protected:
            if not isinstance(path, str) or not PATH_RE.fullmatch(path):
                _fail(f"{case_id}: invalid protected path {path!r}")
            if _path_value(static, path) is MISSING:
                _fail(f"{case_id}: protected path is missing from staticRecord: {path}")

        expectations = _require_list(case.get("expectations"), f"{case_id}.expectations")
        if not expectations:
            _fail(f"{case_id}: expectations must not be empty")
        seen_paths: set[str] = set()
        for expectation in expectations:
            item = _require_object(expectation, f"{case_id}.expectation")
            path = item.get("path")
            if path not in supported or path in seen_paths:
                _fail(f"{case_id}: expectation path is unsupported or duplicated: {path!r}")
            seen_paths.add(path)
            if _path_value(static, path, None) is not None:
                _fail(f"{case_id}: enrichment expectation path is not initially null: {path}")
            expected = item.get("expected")
            matcher = item.get("matcher")
            accepted = _require_list(item.get("acceptedValues"), f"{case_id}.{path}.acceptedValues")
            evidence = _require_list(item.get("evidence"), f"{case_id}.{path}.evidence")
            if expected not in EXPECTED_STATES or matcher not in MATCHERS:
                _fail(f"{case_id}.{path}: invalid expected state or matcher")
            if expected == "present" and (not accepted or not evidence):
                _fail(f"{case_id}.{path}: present labels need accepted values and evidence")
            if expected == "absent" and (accepted or evidence):
                _fail(f"{case_id}.{path}: absent labels must not have values or evidence")
            for span in evidence:
                span = _require_object(span, f"{case_id}.{path}.evidence")
                start, end, quote = span.get("start"), span.get("end"), span.get("quote")
                if (
                    isinstance(start, bool)
                    or isinstance(end, bool)
                    or not isinstance(start, int)
                    or not isinstance(end, int)
                    or not isinstance(quote, str)
                ):
                    _fail(f"{case_id}.{path}: invalid evidence types")
                if start < 0 or end <= start or text[start:end] != quote:
                    _fail(f"{case_id}.{path}: evidence offset or quote mismatch")
            _validate_review(
                item.get("review"),
                f"{case_id}.{path}.review",
                public_release=status == "public_release",
            )

        translations = _require_list(case.get("translationExpectations"), f"{case_id}.translationExpectations")
        for translation in translations:
            item = _require_object(translation, f"{case_id}.translationExpectation")
            path = item.get("path")
            if not isinstance(path, str) or not any(
                path == allowed or path.startswith(allowed + ".") for allowed in translation_paths
            ):
                _fail(f"{case_id}: translation path is outside the allow-list: {path!r}")
            if _path_value(static, path) != item.get("sourceText"):
                _fail(f"{case_id}.{path}: translation sourceText does not match staticRecord")
            references = _require_list(item.get("references"), f"{case_id}.{path}.references")
            if not references or any(not isinstance(reference, str) or not reference for reference in references):
                _fail(f"{case_id}.{path}: translation references must be nonempty text")
            review = _validate_review(
                item.get("review"),
                f"{case_id}.{path}.review",
                public_release=status == "public_release",
            )
            if status == "public_release" and (
                len(references) < 2
            ):
                _fail(f"{case_id}.{path}: public translations require two references")
    return value


def validate_submission(value: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    if value.get("schemaVersion") != SUBMISSION_SCHEMA:
        _fail("unexpected submission schemaVersion")
    if value.get("benchmarkId") != benchmark["benchmarkId"]:
        _fail("submission benchmarkId does not match benchmark")
    systems = _require_object(value.get("systems"), "systems")
    for source in SOURCES:
        system = _require_object(systems.get(source), f"systems.{source}")
        if system.get("accuracyMode") not in {"silver", "gold"}:
            _fail(f"systems.{source}.accuracyMode must be silver or gold")
        repeats = system.get("repeats")
        if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
            _fail(f"systems.{source}.repeats must be a positive integer")
        for field in ("actorId", "buildNumber", "buildId"):
            if not isinstance(system.get(field), str) or not system[field]:
                _fail(f"systems.{source}.{field} must be nonempty text")
        if not BUILD_RE.fullmatch(system["buildNumber"]):
            _fail(f"systems.{source}.buildNumber must be an exact semantic version")
        if type(system.get("translationEnabled")) is not bool:
            _fail(f"systems.{source}.translationEnabled must be a boolean")
        input_digest = system.get("inputSha256")
        if input_digest is not None and (
            not isinstance(input_digest, str) or not SHA256_RE.fullmatch(input_digest)
        ):
            _fail(f"systems.{source}.inputSha256 must be a SHA-256 digest or null")

    cases = {case["caseId"]: case for case in benchmark["cases"]}
    predictions = _require_list(value.get("predictions"), "predictions")
    indexed: dict[tuple[str, int], dict[str, Any]] = {}
    for prediction in predictions:
        item = _require_object(prediction, "prediction")
        case_id, repeat = item.get("caseId"), item.get("repeat")
        if case_id not in cases or isinstance(repeat, bool) or not isinstance(repeat, int):
            _fail(f"prediction has unknown caseId or invalid repeat: {case_id!r}")
        max_repeats = systems[cases[case_id]["source"]]["repeats"]
        if not 1 <= repeat <= max_repeats:
            _fail(f"{case_id}: repeat {repeat} exceeds declared repeats")
        key = (case_id, repeat)
        if key in indexed:
            _fail(f"duplicate prediction for {case_id} repeat {repeat}")
        status, record = item.get("status"), item.get("record")
        if status not in {"completed", "failed"}:
            _fail(f"{case_id}: status must be completed or failed")
        if status == "completed" and not isinstance(record, dict):
            _fail(f"{case_id}: completed prediction requires a record")
        if status == "completed":
            _validate_record_shape(record, f"{case_id}.record")
            source = cases[case_id]["source"]
            if _path_value(record, "identity.source") != source:
                _fail(f"{case_id}.record identity.source does not match case source")
            if benchmark["status"] == "public_release":
                _validate_closed_contract(record, source, f"{case_id}.record")
        if status == "failed" and record is not None:
            _fail(f"{case_id}: failed prediction record must be null")
        indexed[key] = item
    expected_keys = {
        (case_id, repeat)
        for case_id, case in cases.items()
        for repeat in range(1, systems[case["source"]]["repeats"] + 1)
    }
    missing = sorted(expected_keys - set(indexed))
    extra = sorted(set(indexed) - expected_keys)
    if missing or extra:
        _fail(f"submission coverage mismatch: missing={missing[:5]} extra={extra[:5]}")
    value["_indexedPredictions"] = indexed
    return value


def _merge_counts(target: Counter[str], source: Counter[str]) -> None:
    target.update(source)


def score(benchmark: dict[str, Any], submission: dict[str, Any]) -> dict[str, Any]:
    indexed = submission["_indexedPredictions"]
    systems = submission["systems"]
    overall = _new_counts()
    by_source = {source: _new_counts() for source in SOURCES}
    by_path: dict[str, Counter[str]] = {}
    delivery = Counter()
    static_preservation = Counter()
    provenance = Counter()
    translation_scores: dict[str, list[float]] = {source: [] for source in SOURCES}
    translation_invariants = Counter()

    for case in benchmark["cases"]:
        case_id = case["caseId"]
        source = case["source"]
        repeats = systems[source]["repeats"]
        for repeat in range(1, repeats + 1):
            prediction = indexed[(case_id, repeat)]
            delivery["expected"] += 1
            record = prediction["record"] if prediction["status"] == "completed" else None
            if record is not None:
                delivery["completed"] += 1
            else:
                delivery["failed"] += 1

            for expectation in case["expectations"]:
                path = expectation["path"]
                actual = _path_value(record, path) if record is not None else MISSING
                is_match = (
                    expectation["expected"] == "present"
                    and actual is not MISSING
                    and actual is not None
                    and _matches(actual, expectation["acceptedValues"], expectation["matcher"])
                )
                local = _new_counts()
                _update_counts(local, expectation["expected"], actual, is_match)
                _merge_counts(overall, local)
                _merge_counts(by_source[source], local)
                _merge_counts(by_path.setdefault(path, _new_counts()), local)

            if record is not None:
                for path in case["staticProtectedPaths"]:
                    static_preservation["checked"] += 1
                    if _path_value(record, path) == _path_value(case["staticRecord"], path):
                        static_preservation["preserved"] += 1
                    else:
                        static_preservation["changed"] += 1

                filled = _path_value(record, "llm.filledFields", [])
                provenance["recordsChecked"] += 1
                if not isinstance(filled, list) or any(not isinstance(path, str) for path in filled):
                    provenance["invalidRecords"] += 1
                else:
                    actual_fills = {
                        path for path in benchmark["supportedEnrichmentPaths"]
                        if _path_value(case["staticRecord"], path, None) is None
                        and _path_value(record, path, None) is not None
                    }
                    if set(filled) == actual_fills and len(filled) == len(set(filled)):
                        provenance["exactRecords"] += 1
                    else:
                        provenance["mismatchedRecords"] += 1

            if systems[source].get("translationEnabled") is True:
                for item in case["translationExpectations"]:
                    translation_invariants["items"] += 1
                    actual = _path_value(record, item["path"]) if record is not None else MISSING
                    if isinstance(actual, str):
                        translation_scores[source].append(max(_chrf2(actual, ref) for ref in item["references"]))
                        for invariant in item.get("invariants", []):
                            translation_invariants["checked"] += 1
                            if invariant in actual:
                                translation_invariants["preserved"] += 1
                            else:
                                translation_invariants["lost"] += 1
                    else:
                        translation_scores[source].append(0.0)
                        translation_invariants["missingItems"] += 1
                        translation_invariants["checked"] += len(item.get("invariants", []))
                        translation_invariants["lost"] += len(item.get("invariants", []))

    result = {
        "schemaVersion": "nomad-agent-enrichment-score-v1",
        "scorerVersion": SCORER_VERSION,
        "benchmarkId": benchmark["benchmarkId"],
        "submissionId": submission.get("submissionId"),
        "benchmarkStatus": benchmark["status"],
        "systems": systems,
        "metrics": _metrics(overall),
        "bySource": {source: _metrics(counts) for source, counts in by_source.items()},
        "byPath": {path: _metrics(counts) for path, counts in sorted(by_path.items())},
        "delivery": {
            **dict(sorted(delivery.items())),
            "completionRatePct": _ratio(delivery["completed"], delivery["expected"]),
        },
        "staticPreservation": {
            **dict(sorted(static_preservation.items())),
            "preservationRatePct": _ratio(static_preservation["preserved"], static_preservation["checked"]),
        },
        "filledFieldsIntegrity": {
            **dict(sorted(provenance.items())),
            "exactRatePct": _ratio(provenance["exactRecords"], provenance["recordsChecked"]),
        },
        "translation": {
            "bySource": {
                source: {
                    "items": len(scores),
                    "meanBestReferenceChrF2Pct": round(sum(scores) / len(scores), 2) if scores else None,
                }
                for source, scores in translation_scores.items()
            },
            "invariants": {
                **dict(sorted(translation_invariants.items())),
                "preservationRatePct": _ratio(
                    translation_invariants["preserved"], translation_invariants["checked"]
                ),
            },
        },
    }
    return result


def _print_summary(result: dict[str, Any]) -> None:
    metrics = result["metrics"]
    print(f"benchmark: {result['benchmarkId']} ({result['benchmarkStatus']})")
    print(f"submission: {result['submissionId']}")
    print(
        "enrichment: "
        f"precision={metrics['precisionPct']}% recall={metrics['recallPct']}% "
        f"F1={metrics['f1Pct']}% exact={metrics['exactCaseFieldAccuracyPct']}% "
        f"specificity={metrics['specificityPct']}%"
    )
    print(
        f"delivery: {result['delivery']['completed']}/{result['delivery']['expected']} "
        f"({result['delivery']['completionRatePct']}%)"
    )
    print(f"static preservation: {result['staticPreservation']['preservationRatePct']}%")
    print(f"filledFields integrity: {result['filledFieldsIntegrity']['exactRatePct']}%")
    for source in SOURCES:
        values = result["bySource"][source]
        print(
            f"{source}: precision={values['precisionPct']}% recall={values['recallPct']}% "
            f"F1={values['f1Pct']}% specificity={values['specificityPct']}%"
        )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("submission", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        benchmark = validate_benchmark(_read_json(args.benchmark))
        submission = validate_submission(_read_json(args.submission), benchmark)
        result = score(benchmark, submission)
    except ValidationError as exc:
        print(f"benchmark validation failed: {exc}", file=sys.stderr)
        return 2
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
