# Malware analysis shell

A Docker Sandbox workload with Bash, Codex, and the Hybrid Analysis MCP
server. Docker isolates the workload and mediates network access and
credentials; real keys and OAuth tokens stay on the host.

## Start

Requires Docker Sandboxes (`sbx`) v0.45 or newer.

Store the credentials on the host:

```sh
sbx login
sbx secret set hybrid-analysis
sbx secret set openai --oauth
```

Use `sbx secret set openai` for API-key authentication. Do not put credentials
in this repository or in an `.env` file.

Launch the workload in safe mode:

```sh
./start.sh
```

Approve the Hybrid Analysis and OpenAI credential bindings when prompted. The
first run builds a mountless sandbox and opens Bash. No host directory is
mounted. From another host terminal, copy inputs into it:

```sh
sbx cp ./samples malware-sandbox-v1:/home/agent/workspace/
```

```sh
ha-check --live  # Test Hybrid Analysis HTTPS, authentication, and MCP
codex            # Start Codex; /mcp shows hybrid-analysis
exit             # Leave the sandbox shell
```

Copy reports to a disposable host directory and treat them as untrusted:

```sh
mkdir -p ./reports
sbx cp malware-sandbox-v1:/home/agent/workspace/reports/ ./reports/
```

Rerun `start.sh` to return to the same sandbox. Files inside it persist until
the sandbox is removed.

### Convenience mode

For coding or trusted files, mount a host directory read-write:

```sh
./start.sh --rw /path/to/project
```

If the path is omitted, the current directory is mounted. Changes made in the
sandbox immediately affect the host directory. Do not use this mode for
untrusted files. Its default sandbox name is `malware-sandbox-v1-rw`, so it
cannot accidentally reuse the mountless sandbox.

## Architecture

```text
Host
├── sbx CLI
├── OS credential store
└── explicit sbx cp transfers
       │
       ▼
Docker Sandbox VM
└── workload container
    ├── private workspace
    ├── Bash and Codex CLI
    └── Hybrid Analysis MCP server
```

Convenience mode replaces explicit transfers with a read-write host workspace
mount.

### Host and sandbox

`start.sh` selects Docker's managed kit builder and runs `kit/` as an `sbx`
workload. Safe mode creates the sandbox without a host workspace. Convenience
mode passes a host workspace to `sbx`, which mounts it read-write. `sbx` owns
the VM, storage, network policy, and credential proxy.

`kit/malware-sandbox.yaml` is the workload and permission manifest. It declares
the image, allowed hosts, requested credentials, initialization hook, and agent
context.

`kit/malware-sandbox.dockerfile` builds the container. It installs the pinned
Codex CLI and Hybrid Analysis MCP server, then opens Bash as the unprivileged
`agent` user. Dependencies are installed at build time, so package registries
do not need runtime access. `kit/files/mcp-requirements.lock` pins the complete
Python dependency set used by the MCP server.

### OpenAI authentication

```text
Codex → sentinel bearer → Docker proxy → host OAuth token → ChatGPT Codex API
```

`kit/files/configure-codex.py` runs before the shell opens. For OAuth, it
configures Codex to call `chatgpt.com/backend-api/codex` with a sentinel token.
Docker replaces that sentinel with the host token on matching requests. Codex
does not receive the real token.

The same script writes the Codex MCP registration and trusts the sandbox
workspace. Because authentication mode is written during initialization,
create a new sandbox when switching between OAuth and API-key authentication.

### Hybrid Analysis MCP

```text
Codex ↔ JSON-RPC over stdio ↔ local MCP server → Docker proxy → Hybrid Analysis
```

`kit/files/mcp.toml` registers the server with Codex. It is a child process,
not a network service; no MCP port is exposed.

The MCP process sends the `proxy-managed` key sentinel in the `api-key` HTTP
header. Docker replaces it with the Hybrid Analysis key stored on the host.
`kit/files/run-mcp.py` also redirects upstream logs to stderr so stdout remains
a valid MCP JSON-RPC stream.

### Agent context

`kit/context.md` becomes `AGENTS.md` in the workspace. It tells Codex that the
MCP server is available, that credentials are proxy-managed, and that files or
URLs should be submitted only when requested.

### Health check

`ha-check` launches `kit/files/check.py` inside the MCP Python environment.

- `ha-check` checks the credential sentinel, MCP handshake, and tool list.
- `ha-check --live` also calls Hybrid Analysis through the credential proxy
  and runs the MCP `validate_api_key` tool.

Neither check uploads files or URLs, prints secrets, or returns account data.

## Credentials and network

| Service | Container sees | Docker proxy sends |
| --- | --- | --- |
| Hybrid Analysis | `HYBRID_ANALYSIS_KEY=proxy-managed` | Real key in the `api-key` header |
| OpenAI API key | Sentinel API key | Real key in the `Authorization` header |
| ChatGPT OAuth | Sentinel bearer | Host OAuth token to the ChatGPT Codex API |

Runtime HTTPS is limited to the Hybrid Analysis and OpenAI/ChatGPT hosts in
`kit/malware-sandbox.yaml`. Host or organization deny rules still take
precedence. Inspect the effective policy with:

```sh
sbx policy ls malware-sandbox-v1 --type network --wide
```

## Lifecycle

Safe and convenience modes use different sandbox names because workspace
configuration is fixed when a sandbox is created.

```sh
sbx stop malware-sandbox-v1
./start.sh
sbx rm malware-sandbox-v1  # Deletes unexported sandbox files

sbx stop malware-sandbox-v1-rw
./start.sh --rw /path/to/project
sbx rm malware-sandbox-v1-rw  # Mounted host files remain
```

An existing sandbox keeps its original image, authentication mode, and
workspace configuration. Use a new `SANDBOX_NAME` after changing any of them.

## Build notes

`start.sh` sets `SBX_KIT_BUILDER=sandbox`, selecting Docker's OCI-capable
managed builder. To use a host Buildx builder instead:

```sh
docker buildx create --name ha-kit-builder --driver docker-container --bootstrap
SBX_KIT_BUILDER= BUILDX_BUILDER=ha-kit-builder ./start.sh
```

The build needs Docker Hub, GHCR, GitHub, Python release assets, PyPI, and
`files.pythonhosted.org`. A build-time 403 concerns the builder's network
policy, not the workload's runtime policy.

## Versions

- Project release: v1.0.0
- Docker Sandbox workload format: v3
- Codex CLI: 0.162.1
- uv image: `ghcr.io/astral-sh/uv:0.12.0`
- Python: 3.13
- Hybrid Analysis MCP revision: `37404f37d48d1c29409bda49f0f95f658bc205a9`

References: [Docker Sandbox Kit v3](https://docs.docker.com/ai/sandboxes/customize/author/),
[Docker's Codex workload](https://github.com/docker/sandbox-kit-spec/tree/main/examples/codex),
[Hybrid Analysis MCP](https://github.com/PayloadSecurity/hybrid-analysis-mcp-server).

## License

MIT. See `LICENSE`.
