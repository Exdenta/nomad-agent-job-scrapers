from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "setup_linkedin_monitor.py"


def load_module():
    spec = importlib.util.spec_from_file_location("setup_linkedin_monitor", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load setup script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SetupLinkedInMonitorTest(unittest.TestCase):
    def run_setup(
        self,
        target: Path,
        *,
        client: str = "codex",
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--client",
                client,
                "--target",
                str(target),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_codex_setup_is_project_scoped_secret_free_and_idempotent(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            codex_dir = target / ".codex"
            codex_dir.mkdir()
            config = codex_dir / "config.toml"
            config.write_text(
                '[mcp_servers.unrelated]\nurl = "https://example.com/mcp"\n',
                encoding="utf-8",
            )

            first = self.run_setup(target)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_bytes = config.read_bytes()
            parsed = tomllib.loads(first_bytes.decode())
            self.assertEqual(
                parsed["mcp_servers"][module.CODEX_SERVER]["url"],
                module.MCP_URL,
            )
            self.assertEqual(
                parsed["mcp_servers"]["unrelated"]["url"],
                "https://example.com/mcp",
            )
            self.assertNotIn("token", first_bytes.decode().lower())
            self.assertIn(
                f"codex mcp login {module.CODEX_SERVER}", first.stdout
            )

            second = self.run_setup(target)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("Codex MCP config already current", second.stdout)
            self.assertIn("skill already current; keeping", second.stdout)
            self.assertEqual(config.read_bytes(), first_bytes)

    def test_same_name_different_entry_fails_closed_and_preserves_everything(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            codex_dir = target / ".codex"
            codex_dir.mkdir()
            config = codex_dir / "config.toml"
            original = (
                '[mcp_servers.apify_linkedin_jobs]\n'
                'url = "https://mcp.apify.com?tools=broader-unrelated-tool"\n\n'
                '[mcp_servers.apify]\n'
                'url = "https://mcp.apify.com"\n'
            )
            config.write_text(original, encoding="utf-8")

            completed = self.run_setup(target)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("refusing to overwrite", completed.stderr)
            self.assertEqual(config.read_text(encoding="utf-8"), original)
            self.assertFalse((target / ".agents").exists())
            self.assertIn("apify", tomllib.loads(original)["mcp_servers"])
            self.assertEqual(module.CODEX_SERVER, "apify_linkedin_jobs")

    def test_codex_same_url_with_extra_or_different_settings_fails_closed(self) -> None:
        module = load_module()
        variants = {
            "authorization header": (
                'default_tools_approval_mode = "prompt"\n'
                "tool_timeout_sec = 60\n"
                'http_headers = { Authorization = "Bearer secret" }\n'
            ),
            "token environment": (
                'default_tools_approval_mode = "prompt"\n'
                "tool_timeout_sec = 60\n"
                'bearer_token_env_var = "APIFY_TOKEN"\n'
            ),
            "broader approval": (
                'default_tools_approval_mode = "auto"\n'
                "tool_timeout_sec = 60\n"
            ),
            "extra enabled field": (
                'default_tools_approval_mode = "prompt"\n'
                "tool_timeout_sec = 60\n"
                "enabled = true\n"
            ),
        }
        for label, divergent_line in variants.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                codex_dir = target / ".codex"
                codex_dir.mkdir()
                config = codex_dir / "config.toml"
                original = (
                    '[mcp_servers.apify_linkedin_jobs]\n'
                    f"url = {json.dumps(module.MCP_URL)}\n"
                    'auth = "oauth"\n'
                    + divergent_line
                )
                config.write_text(original, encoding="utf-8")
                completed = self.run_setup(target)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("refusing to overwrite", completed.stderr)
                self.assertEqual(config.read_text(encoding="utf-8"), original)
                self.assertFalse((target / ".agents").exists())

    def test_claude_same_url_with_extra_or_different_settings_fails_closed(self) -> None:
        module = load_module()
        variants = {
            "authorization header": {"headers": {"Authorization": "Bearer secret"}},
            "different type": {"type": "sse"},
            "different timeout": {"timeout": 1},
            "extra disabled field": {"disabled": False},
        }
        for label, divergent in variants.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                entry = module.CLAUDE_ENTRY.copy()
                entry.update(divergent)
                original = {"mcpServers": {module.CLAUDE_SERVER: entry}}
                config = target / ".mcp.json"
                config.write_text(
                    json.dumps(original, indent=2) + "\n", encoding="utf-8"
                )
                completed = self.run_setup(target, client="claude")
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("refusing to overwrite", completed.stderr)
                self.assertEqual(
                    json.loads(config.read_text(encoding="utf-8")), original
                )
                self.assertFalse((target / ".claude").exists())

    def test_generic_apify_entries_are_preserved_for_both_clients(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            codex_dir = target / ".codex"
            codex_dir.mkdir()
            codex = codex_dir / "config.toml"
            codex.write_text(
                '[mcp_servers.apify]\nurl = "https://mcp.apify.com"\n',
                encoding="utf-8",
            )
            claude = target / ".mcp.json"
            claude.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "apify": {
                                "type": "http",
                                "url": "https://mcp.apify.com?tools=broader",
                            }
                        }
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            completed = self.run_setup(target, client="both")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            codex_servers = tomllib.loads(codex.read_text(encoding="utf-8"))[
                "mcp_servers"
            ]
            self.assertEqual(codex_servers["apify"]["url"], "https://mcp.apify.com")
            self.assertEqual(
                codex_servers[module.CODEX_SERVER]["url"], module.MCP_URL
            )
            claude_servers = json.loads(claude.read_text(encoding="utf-8"))[
                "mcpServers"
            ]
            self.assertEqual(
                claude_servers["apify"]["url"],
                "https://mcp.apify.com?tools=broader",
            )
            self.assertEqual(
                claude_servers[module.CLAUDE_SERVER]["url"], module.MCP_URL
            )

    def test_both_preflight_blocks_all_writes_on_claude_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            claude = target / ".mcp.json"
            original = {
                "mcpServers": {
                    "apify-linkedin-jobs": {
                        "type": "http",
                        "url": "https://mcp.apify.com?tools=different",
                    },
                    "unrelated": {"command": "example-server"},
                }
            }
            claude.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

            completed = self.run_setup(target, client="both")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("refusing to overwrite", completed.stderr)
            self.assertEqual(json.loads(claude.read_text(encoding="utf-8")), original)
            self.assertFalse((target / ".codex").exists())
            self.assertFalse((target / ".agents").exists())
            self.assertFalse((target / ".claude").exists())

    def test_partial_both_write_recovers_without_touching_first_config(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            updates = module.plan_mcp_configs(target, "both")
            self.assertEqual([update.client for update in updates], ["Codex", "Claude"])
            module.ensure_skill(
                ROOT,
                target,
                client="both",
                force_skill=False,
            )
            module._atomic_write(updates[0])
            codex_config = target / ".codex" / "config.toml"
            first_bytes = codex_config.read_bytes()
            self.assertFalse((target / ".mcp.json").exists())

            completed = self.run_setup(target, client="both")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Codex MCP config already current", completed.stdout)
            self.assertEqual(codex_config.read_bytes(), first_bytes)
            claude = json.loads((target / ".mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(
                claude["mcpServers"][module.CLAUDE_SERVER]["url"],
                module.MCP_URL,
            )

    def test_atomic_write_failure_keeps_existing_config(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            config = target / ".mcp.json"
            original = {"mcpServers": {"unrelated": {"command": "example"}}}
            config.write_text(json.dumps(original) + "\n", encoding="utf-8")
            update = module._plan_claude(target)
            self.assertIsNotNone(update)
            with mock.patch.object(module.os, "replace", side_effect=OSError("stop")):
                with self.assertRaisesRegex(OSError, "stop"):
                    module._atomic_write(update)
            self.assertEqual(json.loads(config.read_text(encoding="utf-8")), original)
            leftovers = list(target.glob("..mcp.json.*"))
            self.assertEqual(leftovers, [])

    def test_modified_skill_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            first = self.run_setup(target)
            self.assertEqual(first.returncode, 0, first.stderr)
            skill_file = (
                target
                / ".agents"
                / "skills"
                / "linkedin-enrich-translate-normalize-scraper"
                / "SKILL.md"
            )
            skill_file.write_text("locally modified\n", encoding="utf-8")
            config = target / ".codex" / "config.toml"
            before = config.read_bytes()

            modified = self.run_setup(target)
            self.assertNotEqual(modified.returncode, 0)
            self.assertIn("refusing to overwrite", modified.stderr)
            self.assertEqual(skill_file.read_text(encoding="utf-8"), "locally modified\n")
            self.assertEqual(config.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
