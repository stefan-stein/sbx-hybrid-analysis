#!/usr/bin/env python3
"""Run the upstream Hybrid Analysis server with stdio-safe logging."""

import logging
import sys
from contextlib import redirect_stdout

# Importing the upstream module installs a root handler that writes application
# logs to stdout. stdout is reserved exclusively for JSON-RPC in stdio MCP.
with redirect_stdout(sys.stderr):
    from mcp_hybrid_analysis import server


def main():
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s: [%(levelname)s] %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    server.mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
