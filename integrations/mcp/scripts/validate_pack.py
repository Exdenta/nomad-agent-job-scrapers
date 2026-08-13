#!/usr/bin/env python3
"""Deterministically validate the tracked MCP v1 integration assets."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tomllib


PACK_DIR = Path(__file__).resolve().parents[1]
PINNED_URL = (
    "https://mcp.apify.com?tools="
    "fetch-actor-details,call-actor,get-actor-run,get-dataset-items,"
    "get-key-value-store-record"
)
LINKEDIN_ACTOR = "nomad-agent/linkedin-enrich-translate-normalize-scraper"
EURAXESS_ACTOR = "nomad-agent/euraxess-enrich-translate-normalize-scraper"
LINKEDIN_BUILD = "0.6.40"
EURAXESS_BUILD = "1.0.9"
CANONICAL_ROOTS = {"custom", "data", "identity", "llm", "raw", "schemaVersion"}
INPUT_KEYS = {
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
}


def _fail(message: str) -> None:
    raise ValueError(message)


def _load_json(relative: str):
    return json.loads((PACK_DIR / relative).read_text(encoding="utf-8"))


def _server_from_json(relative: str, server_name: str, expected_url: str) -> dict:
    value = _load_json(relative)
    servers = value.get("mcpServers")
    if not isinstance(servers, dict) or set(servers) != {server_name}:
        _fail(f"{relative}: expected one {server_name} server")
    server = servers[server_name]
    if not isinstance(server, dict):
        _fail(f"{relative}: server must be an object")
    if server.get("url") != expected_url:
        _fail(f"{relative}: server must use the exact expected URL")
    return server


def _validate_toml_server(
    relative: str,
    server_name: str,
    expected_url: str,
    *,
    token: bool,
) -> None:
    value = tomllib.loads((PACK_DIR / relative).read_text(encoding="utf-8"))
    servers = value.get("mcp_servers", {})
    if set(servers) != {server_name}:
        _fail(f"{relative}: expected one {server_name} server")
    server = servers[server_name]
    if server.get("url") != expected_url:
        _fail(f"{relative}: server must use the exact expected URL")
    if server.get("default_tools_approval_mode") != "prompt":
        _fail(f"{relative}: paid Actor calls must prompt for approval")
    if token and server.get("bearer_token_env_var") != "APIFY_TOKEN":
        _fail(f"{relative}: token config must use bearer_token_env_var")
    if not token and server.get("auth") != "oauth":
        _fail(f"{relative}: OAuth config must declare auth=oauth")


def validate() -> None:
    for relative in (
        "configs/claude-code.oauth.json",
        "configs/claude-code.token.json",
        "configs/cursor.oauth.json",
        "configs/cursor.token.json",
    ):
        _server_from_json(relative, "apify-linkedin-jobs", PINNED_URL)

    claude_oauth = _server_from_json(
        "configs/claude-code.oauth.json", "apify-linkedin-jobs", PINNED_URL
    )
    if claude_oauth.get("type") != "http":
        _fail("Claude Code remote config must declare type=http")
    claude_token = _server_from_json(
        "configs/claude-code.token.json", "apify-linkedin-jobs", PINNED_URL
    )
    if claude_token.get("headers", {}).get("Authorization") != "Bearer ${APIFY_TOKEN}":
        _fail("Claude Code token config must use environment interpolation")
    cursor_token = _server_from_json(
        "configs/cursor.token.json", "apify-linkedin-jobs", PINNED_URL
    )
    if cursor_token.get("headers", {}).get("Authorization") != "Bearer ${env:APIFY_TOKEN}":
        _fail("Cursor token config must use environment interpolation")

    _validate_toml_server(
        "configs/codex.oauth.toml", "apify_linkedin_jobs", PINNED_URL,
        token=False,
    )
    _validate_toml_server(
        "configs/codex.token.toml", "apify_linkedin_jobs", PINNED_URL,
        token=True,
    )

    for relative in (
        "configs/euraxess/claude-code.oauth.json",
        "configs/euraxess/claude-code.token.json",
        "configs/euraxess/cursor.oauth.json",
        "configs/euraxess/cursor.token.json",
    ):
        _server_from_json(relative, "apify-euraxess-jobs", PINNED_URL)
    euraxess_claude = _server_from_json(
        "configs/euraxess/claude-code.oauth.json",
        "apify-euraxess-jobs",
        PINNED_URL,
    )
    if euraxess_claude.get("type") != "http":
        _fail("EURAXESS Claude Code remote config must declare type=http")
    euraxess_claude_token = _server_from_json(
        "configs/euraxess/claude-code.token.json",
        "apify-euraxess-jobs",
        PINNED_URL,
    )
    if euraxess_claude_token.get("headers", {}).get("Authorization") != "Bearer ${APIFY_TOKEN}":
        _fail("EURAXESS Claude Code token config must use environment interpolation")
    euraxess_cursor_token = _server_from_json(
        "configs/euraxess/cursor.token.json",
        "apify-euraxess-jobs",
        PINNED_URL,
    )
    if euraxess_cursor_token.get("headers", {}).get("Authorization") != "Bearer ${env:APIFY_TOKEN}":
        _fail("EURAXESS Cursor token config must use environment interpolation")
    _validate_toml_server(
        "configs/euraxess/codex.oauth.toml",
        "apify_euraxess_jobs",
        PINNED_URL,
        token=False,
    )
    _validate_toml_server(
        "configs/euraxess/codex.token.toml",
        "apify_euraxess_jobs",
        PINNED_URL,
        token=True,
    )

    example = _load_json("examples/linkedin-search.mcp.json")
    if set(example) != {"actor", "input", "waitSecs", "callOptions"}:
        _fail("LinkedIn MCP example must be a complete call-actor envelope")
    if example["actor"] != LINKEDIN_ACTOR:
        _fail("LinkedIn MCP example targets the wrong Actor")
    if example["callOptions"] != {
        "build": LINKEDIN_BUILD,
        "maxItems": 5,
        "maxTotalChargeUsd": 0.1,
    }:
        _fail("LinkedIn MCP example must pin build and both cost caps")
    linkedin_input = example["input"]
    if set(linkedin_input) != INPUT_KEYS:
        _fail("LinkedIn MCP input has missing or unexpected arguments")
    if linkedin_input["schemaVersion"] != "nomad-agent-job-search-input-v1":
        _fail("unsupported input schema version")
    if not 1 <= linkedin_input["maxItems"] <= 5:
        _fail("first-run example must request between 1 and 5 items")
    if linkedin_input["postedWithin"] not in {"1h", "24h", "7d", "30d", "any"}:
        _fail("unsupported postedWithin value")
    if not set(linkedin_input["workArrangements"]) <= {"remote", "hybrid", "onsite"}:
        _fail("unsupported work arrangement")
    for key in (
        "translateToEnglish", "includeRaw", "analyticsEnabled",
    ):
        if linkedin_input[key] is not False:
            _fail(f"bounded example must keep {key}=false")
    if linkedin_input["aiEnrichment"] != {"enabled": False, "accuracy": "silver"}:
        _fail("bounded example must keep Silver AI enrichment disabled")
    if linkedin_input["dedupe"] != {
        "enabled": False,
        "key": "",
    }:
        _fail("bounded example must disable cross-run dedupe")
    if not 0 <= example["waitSecs"] <= 45:
        _fail("Apify MCP waitSecs must be between 0 and 45")

    euraxess = _load_json("examples/euraxess-search.mcp.json")
    if set(euraxess) != {"actor", "input", "waitSecs", "callOptions"}:
        _fail("EURAXESS MCP example must be a complete call-actor envelope")
    if euraxess["actor"] != EURAXESS_ACTOR:
        _fail("EURAXESS MCP example targets the wrong Actor")
    if not 0 <= euraxess["waitSecs"] <= 45:
        _fail("EURAXESS MCP waitSecs must be between 0 and 45")
    call_options = euraxess["callOptions"]
    if call_options != {
        "build": EURAXESS_BUILD,
        "maxItems": 5,
        "maxTotalChargeUsd": 0.1,
    }:
        _fail("EURAXESS MCP example must pin build and both cost caps")
    euraxess_input = euraxess["input"]
    if euraxess_input.get("schemaVersion") != "nomad-agent-job-search-input-v1":
        _fail("EURAXESS MCP example has the wrong input schema")
    if not 1 <= euraxess_input.get("maxItems", 0) <= 5:
        _fail("EURAXESS first-run input must request between 1 and 5 items")
    for key in ("translateToEnglish", "includeRaw", "analyticsEnabled"):
        if euraxess_input.get(key) is not False:
            _fail(f"EURAXESS bounded example must keep {key}=false")
    if euraxess_input.get("aiEnrichment") != {"enabled": False, "accuracy": "silver"}:
        _fail("EURAXESS bounded example must keep Silver AI enrichment disabled")
    if euraxess_input.get("dedupe") != {"enabled": False, "key": ""}:
        _fail("EURAXESS bounded example must disable cross-run dedupe")

    readme = (PACK_DIR / "README.md").read_text(encoding="utf-8")
    for required in (
        PINNED_URL,
        LINKEDIN_BUILD,
        EURAXESS_BUILD,
        "fetch-actor-details",
        "callOptions",
        "deployed input schema",
        "current pricing",
        "get-actor-run",
        "get-dataset-items",
        "get-key-value-store-record",
        "RUN-SUMMARY",
        "nomad-agent-run-summary-v3",
        "SUCCEEDED",
        "RUN-SUMMARY.delivered",
        "terminal run status",
        "one bounded retry",
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
