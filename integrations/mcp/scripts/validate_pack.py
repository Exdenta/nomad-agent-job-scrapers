#!/usr/bin/env python3
"""Deterministically validate the tracked MCP v1 integration assets."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tomllib


PACK_DIR = Path(__file__).resolve().parents[1]
SCOPED_URL = (
    "https://mcp.apify.com?tools="
    "fetch-actor-details,"
    "nomad-agent/linkedin-enrich-translate-normalize-scraper"
)
CANONICAL_ROOTS = {"custom", "data", "identity", "llm", "raw", "schemaVersion"}
EXAMPLE_KEYS = {
    "schemaVersion",
    "keyword",
    "location",
    "postedWithin",
    "workArrangements",
    "maxItems",
    "translateToEnglish",
    "aiEnrichment",
    "includeRaw",
    "dedupe",
    "analyticsEnabled",
    "waitSecs",
}


def _fail(message: str) -> None:
    raise ValueError(message)


def _load_json(relative: str):
    return json.loads((PACK_DIR / relative).read_text(encoding="utf-8"))


def _server_from_json(relative: str) -> dict:
    value = _load_json(relative)
    servers = value.get("mcpServers")
    if not isinstance(servers, dict) or set(servers) != {"apify-linkedin-jobs"}:
        _fail(f"{relative}: expected one apify-linkedin-jobs server")
    server = servers["apify-linkedin-jobs"]
    if not isinstance(server, dict):
        _fail(f"{relative}: server must be an object")
    if server.get("url") != SCOPED_URL:
        _fail(f"{relative}: server must use the exact scoped URL")
    return server


def validate() -> None:
    for relative in (
        "configs/claude-code.oauth.json",
        "configs/claude-code.token.json",
        "configs/cursor.oauth.json",
        "configs/cursor.token.json",
    ):
        _server_from_json(relative)

    claude_oauth = _server_from_json("configs/claude-code.oauth.json")
    if claude_oauth.get("type") != "http":
        _fail("Claude Code remote config must declare type=http")
    claude_token = _server_from_json("configs/claude-code.token.json")
    if claude_token.get("headers", {}).get("Authorization") != "Bearer ${APIFY_TOKEN}":
        _fail("Claude Code token config must use environment interpolation")
    cursor_token = _server_from_json("configs/cursor.token.json")
    if cursor_token.get("headers", {}).get("Authorization") != "Bearer ${env:APIFY_TOKEN}":
        _fail("Cursor token config must use environment interpolation")

    for relative in ("configs/codex.oauth.toml", "configs/codex.token.toml"):
        value = tomllib.loads((PACK_DIR / relative).read_text(encoding="utf-8"))
        servers = value.get("mcp_servers", {})
        if set(servers) != {"apify_linkedin_jobs"}:
            _fail(f"{relative}: expected one apify_linkedin_jobs server")
        server = servers["apify_linkedin_jobs"]
        if server.get("url") != SCOPED_URL:
            _fail(f"{relative}: server must use the exact scoped URL")
        if server.get("default_tools_approval_mode") != "prompt":
            _fail(f"{relative}: paid Actor calls must prompt for approval")
    token_toml = tomllib.loads(
        (PACK_DIR / "configs/codex.token.toml").read_text(encoding="utf-8")
    )
    if token_toml["mcp_servers"]["apify_linkedin_jobs"].get(
        "bearer_token_env_var"
    ) != "APIFY_TOKEN":
        _fail("Codex token config must use bearer_token_env_var")

    example = _load_json("examples/linkedin-search.mcp.json")
    if set(example) != EXAMPLE_KEYS:
        _fail("MCP example has missing or unexpected arguments")
    if example["schemaVersion"] != "nomad-agent-job-search-input-v1":
        _fail("unsupported input schema version")
    if not 1 <= example["maxItems"] <= 5:
        _fail("first-run example must request between 1 and 5 items")
    if example["postedWithin"] not in {"1h", "24h", "7d", "30d", "any"}:
        _fail("unsupported postedWithin value")
    if not set(example["workArrangements"]) <= {"remote", "hybrid", "onsite"}:
        _fail("unsupported work arrangement")
    for key in (
        "translateToEnglish", "includeRaw", "analyticsEnabled",
    ):
        if example[key] is not False:
            _fail(f"bounded example must keep {key}=false")
    if example["aiEnrichment"] != {"enabled": False, "accuracy": "silver"}:
        _fail("bounded example must keep Silver AI enrichment disabled")
    if example["dedupe"] != {
        "enabled": False,
        "key": "",
    }:
        _fail("bounded example must disable cross-run dedupe")
    if not 0 <= example["waitSecs"] <= 45:
        _fail("Apify MCP waitSecs must be between 0 and 45")

    readme = (PACK_DIR / "README.md").read_text(encoding="utf-8")
    for required in (
        SCOPED_URL,
        "fetch-actor-details",
        "deployed input schema",
        "current pricing",
        "get-actor-run",
        "get-dataset-items",
        "SUCCEEDED",
        "itemCount: 0",
        "ChatGPT web",
        "Business, Enterprise, and Edu",
    ):
        if required not in readme:
            _fail(f"README is missing required behavior: {required}")
    if set(re.findall(r"`(custom|data|identity|llm|raw|schemaVersion)`", readme)) != CANONICAL_ROOTS:
        _fail("README must name all six canonical roots")

    for path in PACK_DIR.rglob("*"):
        if not path.is_file() or path.suffix in {".pyc"}:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"apify_api_[A-Za-z0-9]+", text):
            _fail(f"{path.relative_to(PACK_DIR)} contains an Apify token")


def main() -> int:
    try:
        validate()
    except (OSError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"MCP pack validation failed: {exc}", file=sys.stderr)
        return 1
    print("MCP pack validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
