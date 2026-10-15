#!/usr/bin/env python3
"""Run inside the sandbox. Handshake by default; --live checks key injection."""

import asyncio
import argparse
import json
import os

import httpx
import truststore
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(live):
    if os.environ.get("HYBRID_ANALYSIS_KEY") != "proxy-managed":
        raise SystemExit(
            "Expected Docker's proxy-managed sentinel. Store the hybrid-analysis "
            "secret and approve its credential binding before running this check."
        )
    truststore.inject_into_ssl()
    if live:
        # Check the actual HTTP status too: upstream tool error normalization
        # can otherwise report a failed request as a successful key validation.
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://hybrid-analysis.com/api/v2/key/current",
                headers={
                    "api-key": os.environ["HYBRID_ANALYSIS_KEY"],
                    "User-Agent": "HybridAnalysisMCP/1.0",
                    "accept": "application/json",
                },
            )
            if response.status_code != 200:
                raise SystemExit(
                    f"Hybrid Analysis returned HTTP {response.status_code}; "
                    "check network policy, the stored API key, and its binding."
                )
            if not isinstance(response.json(), dict):
                raise SystemExit("Hybrid Analysis returned an unexpected response.")
        print("PASS: HTTPS access and host-side api-key injection")

    parameters = StdioServerParameters(
        command="/opt/hybrid-analysis/venv/bin/python",
        args=["/usr/local/lib/malware-sandbox/run-mcp.py"],
        env={
            **os.environ,
            "MCP_TRANSPORT": "stdio",
            "HYBRID_ANALYSIS_API_URL": "https://hybrid-analysis.com/api/v2",
        },
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            expected = {"validate_api_key", "search_by_hash", "submit_file", "submit_url"}
            if not expected <= names:
                raise SystemExit("The MCP server did not expose the expected tools.")
            print(f"PASS: stdio MCP handshake ({len(names)} tools)")
            if live:
                result = await session.call_tool("validate_api_key", {})
                data = result.structuredContent
                if not data:
                    for item in result.content:
                        if getattr(item, "type", None) == "text":
                            try:
                                data = json.loads(item.text)
                                break
                            except (ValueError, TypeError):
                                continue
                if result.isError or not isinstance(data, dict) or data.get("status") != "valid":
                    raise SystemExit("The MCP validate_api_key call failed.")
                print("PASS: MCP validate_api_key tool call")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check the Hybrid Analysis MCP integration.")
    parser.add_argument("--live", action="store_true", help="also verify live API authentication")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.live))
    except (httpx.HTTPError, ValueError):
        raise SystemExit("HTTPS check failed; verify connectivity and the sandbox proxy CA.") from None
