from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "integrations" / "shared" / "retry_policy.py"
spec = importlib.util.spec_from_file_location("nomad_retry_policy", MODULE_PATH)
assert spec and spec.loader
retry_policy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = retry_policy
spec.loader.exec_module(retry_policy)


def summary(*, recommended: bool = True, blocked: bool = True) -> dict[str, object]:
    return {
        "schemaVersion": "nomad-agent-linkedin-run-summary-v1",
        "blocked": blocked,
        "reschedule": {
            "recommended": recommended,
            "afterSeconds": 60 if recommended else None,
            "notBefore": "2026-08-10T12:01:00Z" if recommended else None,
        },
    }


class RetryPolicyTest(unittest.TestCase):
    def test_honors_remaining_not_before_delay(self) -> None:
        decision = retry_policy.evaluate_run_summary(
            summary(),
            now=datetime(2026, 8, 10, 12, 0, 15, tzinfo=timezone.utc),
        )
        self.assertTrue(decision.recommended)
        self.assertEqual(decision.delay_seconds, 45)

    def test_missing_and_non_recommended_summaries_do_not_retry(self) -> None:
        self.assertFalse(retry_policy.evaluate_run_summary(None).recommended)
        self.assertFalse(
            retry_policy.evaluate_run_summary(summary(recommended=False)).recommended
        )

    def test_recommended_retry_requires_blocked_and_valid_delay(self) -> None:
        with self.assertRaisesRegex(retry_policy.RunSummaryError, "blocked=true"):
            retry_policy.evaluate_run_summary(summary(blocked=False))
        malformed = summary()
        malformed["reschedule"]["afterSeconds"] = 3_601
        with self.assertRaisesRegex(retry_policy.RunSummaryError, "1 to 3600"):
            retry_policy.evaluate_run_summary(malformed)

    def test_unknown_version_fails_closed(self) -> None:
        value = summary()
        value["schemaVersion"] = "nomad-agent-linkedin-run-summary-v2"
        with self.assertRaisesRegex(retry_policy.RunSummaryError, "unsupported"):
            retry_policy.evaluate_run_summary(value)


if __name__ == "__main__":
    unittest.main()
