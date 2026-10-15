Codex is available from this sandbox's shell. The hybrid-analysis MCP server
runs locally over stdio and can access the workspace. In the default safe mode,
the workspace is private to the sandbox and files move through `sbx cp`. In
`--rw` convenience mode, it is a read-write host mount.

Credentials are sent by the host proxy; never request or print API keys.
Use hash searches or existing reports when possible. Submit files or URLs
only when requested.

The shell command `ha-check --live` verifies actual HTTP authentication as
well as the MCP connection.
