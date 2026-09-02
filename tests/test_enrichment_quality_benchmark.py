from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "enrichment-quality-v1"


def _load_scorer():
    spec = importlib.util.spec_from_file_location(
        "public_enrichment_quality_score", BENCHMARK / "score.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load public enrichment scorer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCORER = _load_scorer()


class EnrichmentQualityBenchmarkTest(unittest.TestCase):
    def _read(self, name: str):
        return json.loads((BENCHMARK / name).read_text(encoding="utf-8"))

    def test_synthetic_sample_is_perfect_and_source_stratified(self):
        benchmark = SCORER.validate_benchmark(self._read("benchmark.sample.json"))
        submission = SCORER.validate_submission(
            self._read("predictions.sample.json"), benchmark
        )
        result = SCORER.score(benchmark, submission)
        self.assertEqual(result["metrics"]["f1Pct"], 100.0)
        self.assertEqual(result["bySource"]["linkedin"]["f1Pct"], 100.0)
        self.assertEqual(result["bySource"]["euraxess"]["f1Pct"], 100.0)
        self.assertEqual(result["staticPreservation"]["preservationRatePct"], 100.0)
        self.assertEqual(result["filledFieldsIntegrity"]["exactRatePct"], 100.0)
        self.assertEqual(
            result["translation"]["bySource"]["euraxess"]["meanBestReferenceChrF2Pct"],
            100.0,
        )

    def test_public_release_requires_closed_static_contract(self):
        benchmark = self._read("benchmark.sample.json")
        benchmark["status"] = "public_release"
        with self.assertRaisesRegex(SCORER.ValidationError, "closed linkedin output contract"):
            SCORER.validate_benchmark(benchmark)

    def test_public_release_rejects_draft_labels(self):
        with self.assertRaisesRegex(SCORER.ValidationError, "human gold review"):
            SCORER._validate_review(
                {
                    "labelQuality": "draft",
                    "independentHumanReviewers": 0,
                    "adjudicated": False,
                },
                "review",
                public_release=True,
            )

    def test_submission_requires_every_declared_repeat(self):
        benchmark = SCORER.validate_benchmark(self._read("benchmark.sample.json"))
        submission = self._read("predictions.sample.json")
        submission["systems"]["linkedin"]["repeats"] = 2
        with self.assertRaises(SCORER.ValidationError):
            SCORER.validate_submission(submission, benchmark)

    def test_human_review_plan_is_publicly_linked_and_release_gated(self):
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        benchmark_readme = (BENCHMARK / "README.md").read_text(encoding="utf-8")
        review_plan = (BENCHMARK / "HUMAN_REVIEW_PLAN.md").read_text(encoding="utf-8")
        release_checklist = (BENCHMARK / "RELEASE_CHECKLIST.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("benchmarks/enrichment-quality-v1/HUMAN_REVIEW_PLAN.md", root_readme)
        self.assertIn("HUMAN_REVIEW_PLAN.md", benchmark_readme)
        self.assertIn("two independent first-pass annotations", review_plan)
        self.assertIn("Pseudonymous first-pass labels", release_checklist)


if __name__ == "__main__":
    unittest.main()
