from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "integrations" / "shared" / "retry_policy.py"
sys.path.insert(0, str(MODULE_PATH.parent))
spec = importlib.util.spec_from_file_location("nomad_retry_policy", MODULE_PATH)
assert spec and spec.loader
retry_policy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = retry_policy
spec.loader.exec_module(retry_policy)


class RetryPolicyTest(unittest.TestCase):
    @staticmethod
    def summary(status: str = "succeeded", delivered: int = 1) -> dict:
        source_status = status
        cards = 0 if status == "empty" else delivered
        degraded = status in {"partial", "failed", "deadline"}
        return {
            "schemaVersion": "nomad-agent-fleet-run-summary-v2",
            "status": status,
            "startedAt": "2026-08-13T10:00:00Z",
            "finishedAt": "2026-08-13T10:01:00Z",
            "partial": status in {"partial", "deadline"},
            "truncated": False,
            "delivered": delivered,
            "sources": {
                "linkedin": {
                    "status": source_status,
                    "searchRequests": 1,
                    "cardsSeen": cards,
                    "detailsCompleted": cards,
                    "normalized": cards,
                    "afterFilters": cards,
                    "deliveryEligible": delivered,
                    "delivered": delivered,
                    "stale": False,
                    "blocked": False,
                    "stopReason": "source-failure" if degraded else None,
                    "errors": [],
                }
            },
        }

    def test_success_fetches_dataset_without_automatic_retry(self) -> None:
        decision = retry_policy.evaluate_terminal_run({
            "status": "SUCCEEDED", "exitCode": 0,
        }, self.summary())
        self.assertTrue(decision.fetch_dataset)
        self.assertFalse(decision.automatic_retry)
        self.assertEqual(decision.summary_status, "succeeded")

    def test_mcp_success_may_omit_exit_code(self) -> None:
        decision = retry_policy.evaluate_terminal_run(
            {"status": "SUCCEEDED"}, self.summary("empty", 0),
        )
        self.assertTrue(decision.fetch_dataset)
        self.assertFalse(decision.automatic_retry)

    def test_missing_or_degraded_summary_blocks_delivery_without_retry(self) -> None:
        missing = retry_policy.evaluate_terminal_run({"status": "SUCCEEDED"})
        self.assertFalse(missing.fetch_dataset)
        self.assertFalse(missing.automatic_retry)
        self.assertEqual(missing.reason, "missing-run-summary")
        for status in ("partial", "failed", "deadline"):
            with self.subTest(status=status):
                decision = retry_policy.evaluate_terminal_run(
                    {"status": "SUCCEEDED"}, self.summary(status, 0),
                )
                self.assertFalse(decision.fetch_dataset)
                self.assertFalse(decision.automatic_retry)

    def test_dataset_count_must_equal_summary_delivered(self) -> None:
        retry_policy.validate_dataset_count(self.summary(delivered=2), 2)
        with self.assertRaisesRegex(retry_policy.RunStateError, "does not match"):
            retry_policy.validate_dataset_count(self.summary(delivered=2), 1)

    def test_failed_terminal_states_never_fetch_or_retry(self) -> None:
        for status in ("FAILED", "ABORTED", "TIMED-OUT"):
            with self.subTest(status=status):
                decision = retry_policy.evaluate_terminal_run({
                    "status": status, "exitCode": 1,
                })
                self.assertFalse(decision.fetch_dataset)
                self.assertFalse(decision.automatic_retry)

    def test_nonterminal_and_malformed_metadata_fail_closed(self) -> None:
        with self.assertRaisesRegex(retry_policy.RunStateError, "not terminal"):
            retry_policy.evaluate_terminal_run({"status": "RUNNING"})
        with self.assertRaisesRegex(retry_policy.RunStateError, "exitCode"):
            retry_policy.evaluate_terminal_run({
                "status": "SUCCEEDED", "exitCode": "0",
            })


if __name__ == "__main__":
    unittest.main()
