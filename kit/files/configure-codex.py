#!/usr/bin/env python3
"""Seed this v3 workload's own Codex configuration before the shell opens."""

import json
import os
from pathlib import Path


def render_config(mode, workspace, mcp_config):
    # Docker provides the outer isolation. These match its Codex kit defaults.
    top = [
        'approval_policy = "never"',
        'sandbox_mode = "danger-full-access"',
        'mcp_oauth_credentials_store = "file"',
    ]
    if mode in {"oauth", "apikey"}:
        top.append('forced_login_method = "api"')
    if mode == "oauth":
        top.append('model_provider = "sandboxd"')
    config = "\n".join(top) + "\n\n" + mcp_config.rstrip() + "\n"
    if mode == "oauth":
        config += '''
[model_providers.sandboxd]
name = "Sandbox Proxy"
base_url = "https://chatgpt.com/backend-api/codex"
experimental_bearer_token = "oai-oat01-proxy-managed"
requires_openai_auth = false
'''
    config += f'\n[projects.{json.dumps(workspace, ensure_ascii=False)}]\ntrust_level = "trusted"\n'
    return config


def configure(config_dir, mode, workspace, mcp_config):
    if mode not in {"none", "oauth", "apikey"}:
        raise ValueError(f"Unsupported OpenAI credential mode: {mode!r}")
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.toml").write_text(render_config(mode, workspace, mcp_config))
    auth = config_dir / "auth.json"
    if mode in {"oauth", "apikey"}:
        # This is a sentinel, never a real API key or ChatGPT token.
        auth.write_text(json.dumps({"OPENAI_API_KEY": "proxy-managed"}) + "\n")
        auth.chmod(0o600)
    else:
        auth.unlink(missing_ok=True)


if __name__ == "__main__":
    configure(
        Path("/home/agent/.codex"),
        os.environ.get("SBX_CRED_OPENAI_MODE", "none"),
        os.environ.get("WORKSPACE_DIR", "/home/agent/workspace"),
        Path(__file__).with_name("mcp.toml").read_text(),
    )
