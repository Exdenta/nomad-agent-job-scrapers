from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
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
    def summary(
        status: str = "succeeded",
        delivered: int = 1,
        *,
        retry: bool = False,
    ) -> dict:
        return {
            "schemaVersion": "nomad-agent-run-summary-v3",
            "status": status,
            "startedAt": "2026-08-13T10:00:00Z",
            "finishedAt": "2026-08-13T10:01:00Z",
            "truncated": False,
            "delivered": delivered,
            "retry": {
                "recommended": retry,
                "afterSeconds": 60 if retry else None,
                "notBefore": "2026-08-13T10:02:00Z" if retry else None,
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

    def test_missing_summary_blocks_delivery(self) -> None:
        missing = retry_policy.evaluate_terminal_run({"status": "SUCCEEDED"})
        self.assertFalse(missing.fetch_dataset)
        self.assertFalse(missing.automatic_retry)
        self.assertEqual(missing.reason, "missing-run-summary")

    def test_partial_can_request_one_bounded_retry(self) -> None:
        now = datetime(2026, 8, 13, 10, 1, tzinfo=timezone.utc)
        summary = self.summary("partial", 1, retry=True)
        first = retry_policy.evaluate_terminal_run(
            {"status": "SUCCEEDED", "exitCode": 0},
            summary,
            retry_attempt=0,
            now=now,
        )
        self.assertFalse(first.fetch_dataset)
        self.assertTrue(first.automatic_retry)
        self.assertEqual(first.delay_seconds, 60)

        exhausted = retry_policy.evaluate_terminal_run(
            {"status": "SUCCEEDED", "exitCode": 0},
            summary,
            retry_attempt=1,
            now=now,
        )
        self.assertTrue(exhausted.fetch_dataset)
        self.assertFalse(exhausted.automatic_retry)
        self.assertEqual(exhausted.reason, "retry-bound-exhausted")

    def test_partial_without_retry_is_usable(self) -> None:
        decision = retry_policy.evaluate_terminal_run(
            {"status": "SUCCEEDED", "exitCode": 0},
            self.summary("partial", 1),
        )
        self.assertTrue(decision.fetch_dataset)
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
