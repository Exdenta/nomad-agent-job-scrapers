from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "integrations" / "mcp"
SCOPED_URL = (
    "https://mcp.apify.com?tools="
    "fetch-actor-details,"
    "nomad-agent/linkedin-enrich-translate-normalize-scraper"
)


class McpPackTests(unittest.TestCase):
    def test_offline_validator_passes(self):
        result = subprocess.run(
            [sys.executable, str(PACK / "scripts" / "validate_pack.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MCP pack validation passed", result.stdout)

    def test_json_configs_are_scoped_and_secret_free(self):
        for path in sorted((PACK / "configs").glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            server = value["mcpServers"]["apify-linkedin-jobs"]
            self.assertEqual(server["url"], SCOPED_URL)
            self.assertNotIn("apify_api_", path.read_text(encoding="utf-8"))
        claude = json.loads(
            (PACK / "configs" / "claude-code.oauth.json").read_text(encoding="utf-8")
        )
        self.assertEqual(claude["mcpServers"]["apify-linkedin-jobs"]["type"], "http")

    def test_codex_token_is_environment_backed(self):
        value = tomllib.loads(
            (PACK / "configs" / "codex.token.toml").read_text(encoding="utf-8")
        )
        server = value["mcp_servers"]["apify_linkedin_jobs"]
        self.assertEqual(server["url"], SCOPED_URL)
        self.assertEqual(server["bearer_token_env_var"], "APIFY_TOKEN")
        self.assertEqual(server["default_tools_approval_mode"], "prompt")

    def test_bounded_example_is_storage_free_and_inexpensive(self):
        value = json.loads(
            (PACK / "examples" / "linkedin-search.mcp.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertLessEqual(value["maxItems"], 5)
        self.assertFalse(value["translateToEnglish"])
        self.assertEqual(
            value["aiEnrichment"],
            {"enabled": False, "accuracy": "silver"},
        )
        self.assertFalse(value["includeRaw"])
        self.assertFalse(value["analyticsEnabled"])
        self.assertEqual(
            value["dedupe"],
            {"enabled": False, "key": ""},
        )

    def test_smoke_response_decoder_accepts_json_and_sse(self):
        path = PACK / "scripts" / "smoke_test.py"
        spec = importlib.util.spec_from_file_location("mcp_smoke_test", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(module.SCOPED_URL, SCOPED_URL)
        self.assertIn("fetch-actor-details", module.REQUIRED_TOOLS)
        self.assertIn("get-key-value-store-record", module.REQUIRED_TOOLS)
        direct = module._decode_response(
            b'{"jsonrpc":"2.0","id":7,"result":{"ok":true}}',
            "application/json",
            7,
        )
        self.assertEqual(direct["result"], {"ok": True})
        sse = module._decode_response(
            b'event: message\ndata: {"jsonrpc":"2.0","id":7,"result":{"ok":true}}\n\n',
            "text/event-stream",
            7,
        )
        self.assertEqual(sse["result"], {"ok": True})
        self.assertEqual(
            module._default_storage_id(
                {
                    "storages": {
                        "keyValueStores": {"default": {"id": "store-1"}}
                    }
                },
                "keyValueStores",
                "defaultKeyValueStoreId",
            ),
            "store-1",
        )

    def test_smoke_script_honors_only_structured_bounded_retry(self):
        text = (PACK / "scripts" / "smoke_test.py").read_text(encoding="utf-8")
        self.assertIn('"get-key-value-store-record"', text)
        self.assertIn('"recordKey": "RUN-SUMMARY"', text)
        self.assertIn("evaluate_run_summary", text)
        self.assertIn("--max-reschedule-retries", text)
        self.assertIn("time.sleep(decision.delay_seconds)", text)


if __name__ == "__main__":
    unittest.main()
