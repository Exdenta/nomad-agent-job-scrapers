from __future__ import annotations

import importlib.util
from http.client import IncompleteRead
import json
from pathlib import Path
import subprocess
import sys
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "integrations" / "mcp"
PINNED_URL = (
    "https://mcp.apify.com?tools="
    "fetch-actor-details,call-actor,get-actor-run,get-dataset-items,"
    "get-key-value-store-record"
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
            self.assertEqual(server["url"], PINNED_URL)
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
        self.assertEqual(server["url"], PINNED_URL)
        self.assertEqual(server["bearer_token_env_var"], "APIFY_TOKEN")
        self.assertEqual(server["default_tools_approval_mode"], "prompt")

    def test_bounded_example_is_storage_free_and_inexpensive(self):
        value = json.loads(
            (PACK / "examples" / "linkedin-search.mcp.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(value["actor"], "nomad-agent/linkedin-enrich-translate-normalize-scraper")
        self.assertEqual(value["callOptions"]["build"], "0.6.41")
        actor_input = value["input"]
        self.assertLessEqual(actor_input["maxItems"], 5)
        self.assertFalse(actor_input["translateToEnglish"])
        self.assertEqual(
            actor_input["aiEnrichment"],
            {"enabled": False, "accuracy": "silver"},
        )
        self.assertFalse(actor_input["includeRaw"])
        self.assertFalse(actor_input["analyticsEnabled"])
        self.assertEqual(
            actor_input["dedupe"],
            {"enabled": False, "key": ""},
        )

    def test_euraxess_configs_have_oauth_and_token_parity(self):
        config_dir = PACK / "configs" / "euraxess"
        self.assertEqual(
            {path.name for path in config_dir.iterdir()},
            {
                "claude-code.oauth.json", "claude-code.token.json",
                "codex.oauth.toml", "codex.token.toml",
                "cursor.oauth.json", "cursor.token.json",
            },
        )
        for filename in (
            "claude-code.oauth.json", "claude-code.token.json",
            "cursor.oauth.json", "cursor.token.json",
        ):
            value = json.loads((config_dir / filename).read_text(encoding="utf-8"))
            server = value["mcpServers"]["apify-euraxess-jobs"]
            self.assertEqual(server["url"], PINNED_URL)
        for filename in ("codex.oauth.toml", "codex.token.toml"):
            value = tomllib.loads((config_dir / filename).read_text(encoding="utf-8"))
            server = value["mcp_servers"]["apify_euraxess_jobs"]
            self.assertEqual(server["url"], PINNED_URL)
            self.assertEqual(server["default_tools_approval_mode"], "prompt")
        token = tomllib.loads((config_dir / "codex.token.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            token["mcp_servers"]["apify_euraxess_jobs"]["bearer_token_env_var"],
            "APIFY_TOKEN",
        )

    def test_euraxess_example_pins_current_canary_build_and_cost_caps(self):
        value = json.loads(
            (PACK / "examples" / "euraxess-search.mcp.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            value["actor"],
            "nomad-agent/euraxess-enrich-translate-normalize-scraper",
        )
        self.assertEqual(value["callOptions"], {
            "build": "1.0.10",
            "maxItems": 5,
            "maxTotalChargeUsd": 0.1,
        })
        self.assertLessEqual(value["input"]["maxItems"], 5)
        self.assertFalse(value["input"]["translateToEnglish"])
        self.assertFalse(value["input"]["aiEnrichment"]["enabled"])

    def test_smoke_response_decoder_accepts_json_and_sse(self):
        path = PACK / "scripts" / "smoke_test.py"
        spec = importlib.util.spec_from_file_location("mcp_smoke_test", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(module.SCOPED_URL, PINNED_URL)
        self.assertEqual(module.PROFILES["linkedin"]["build"], "0.6.41")
        self.assertEqual(module.PROFILES["linkedin"]["tool"], "call-actor")
        self.assertEqual(module.PROFILES["euraxess"]["url"], PINNED_URL)
        self.assertEqual(module.PROFILES["euraxess"]["tool"], "call-actor")
        self.assertEqual(module.PROFILES["euraxess"]["build"], "1.0.10")
        self.assertIn("fetch-actor-details", module.REQUIRED_TOOLS)
        self.assertIn("call-actor", module.REQUIRED_TOOLS)
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

    def test_smoke_script_uses_v4_status_and_at_most_one_retry(self):
        text = (PACK / "scripts" / "smoke_test.py").read_text(encoding="utf-8")
        self.assertIn('"get-key-value-store-record"', text)
        self.assertIn("RUN-SUMMARY", text)
        self.assertIn("validate_dataset_count", text)
        self.assertIn("--max-reschedule-retries", text)
        self.assertIn("time.sleep", text)
        self.assertIn("retry_attempt", text)
        self.assertIn("max_retries", text)
        self.assertNotIn("sources.linkedin", text)
        self.assertNotIn("sources.euraxess", text)
        self.assertIn('"--profile"', text)
        self.assertIn('"euraxess"', text)
        self.assertIn('call_options.get("build")', text)
        self.assertIn("_verified_rest_run", text)
        self.assertIn("evaluate_terminal_run", text)
        self.assertIn("_require_build(run", text)

    def test_smoke_transport_retries_only_idempotent_mcp_reads(self):
        path = PACK / "scripts" / "smoke_test.py"
        spec = importlib.util.spec_from_file_location("mcp_smoke_retry", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        class FlakyClient:
            def __init__(self):
                self.calls = 0

            def call(self, _method, _params):
                self.calls += 1
                raise IncompleteRead(b"")

        read_client = FlakyClient()
        with self.assertRaises(IncompleteRead):
            module._call_tool(read_client, "get-actor-run", {"runId": "r"})
        self.assertEqual(read_client.calls, 3)

        paid_client = FlakyClient()
        with self.assertRaises(IncompleteRead):
            module._call_tool(paid_client, "call-actor", {"actor": "a"})
        self.assertEqual(paid_client.calls, 1)


if __name__ == "__main__":
    unittest.main()
