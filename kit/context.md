Codex is available from this sandbox's shell. The hybrid-analysis MCP server
runs locally over stdio and can access the workspace. In the default safe mode,
the workspace is private to the sandbox and files move through `sbx cp`. In
`--rw` convenience mode, it is a read-write host mount.

Credentials are sent by the host proxy; never request or print API keys.
For SHA256 investigations, prefer the aggregated Labs sample overview; use
quick scans for fast file triage and full submissions for behavioral analysis.
Submit files or URLs, and create, update, or delete YARA hunting rules, only
when requested. Deleting a YARA rule is irreversible.

The shell command `ha-check --live` verifies actual HTTP authentication as
well as the MCP connection.
