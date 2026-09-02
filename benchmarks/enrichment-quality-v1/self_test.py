#!/usr/bin/env python3
"""Offline checks for the public benchmark scorer and synthetic fixtures."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def _load_scorer():
    spec = importlib.util.spec_from_file_location("enrichment_quality_score", ROOT / "score.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load score.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    scorer = _load_scorer()
    benchmark = scorer.validate_benchmark(_read("benchmark.sample.json"))
    submission = scorer.validate_submission(_read("predictions.sample.json"), benchmark)
    result = scorer.score(benchmark, submission)
    assert result["metrics"]["precisionPct"] == 100.0
    assert result["metrics"]["recallPct"] == 100.0
    assert result["metrics"]["specificityPct"] == 100.0
    assert result["delivery"]["completionRatePct"] == 100.0
    assert result["staticPreservation"]["preservationRatePct"] == 100.0
    assert result["filledFieldsIntegrity"]["exactRatePct"] == 100.0
    assert result["translation"]["bySource"]["euraxess"]["meanBestReferenceChrF2Pct"] == 100.0

    wrong = _read("predictions.sample.json")
    wrong["predictions"][0]["record"]["data"]["application"]["selectionProcess"] = "Interview"
    wrong["predictions"][0]["record"]["llm"]["filledFields"].append(
        "data.application.selectionProcess"
    )
    wrong_submission = scorer.validate_submission(wrong, benchmark)
    wrong_result = scorer.score(benchmark, wrong_submission)
    assert wrong_result["metrics"]["unsupportedFill"] == 1
    assert wrong_result["metrics"]["specificityPct"] == 50.0

    changed = _read("predictions.sample.json")
    changed["predictions"][0]["record"]["data"]["title"] = "Changed title"
    changed_submission = scorer.validate_submission(changed, benchmark)
    changed_result = scorer.score(benchmark, changed_submission)
    assert changed_result["staticPreservation"]["changed"] == 1

    bad_benchmark = copy.deepcopy(_read("benchmark.sample.json"))
    bad_benchmark["cases"][0]["expectations"][0]["evidence"][0]["start"] = 1
    try:
        scorer.validate_benchmark(bad_benchmark)
    except scorer.ValidationError:
        pass
    else:
        raise AssertionError("invalid evidence offsets were accepted")
    print("enrichment quality benchmark self-test passed")


if __name__ == "__main__":
    main()
