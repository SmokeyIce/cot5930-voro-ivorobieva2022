# HW4: Authentication Log MCP

A local MCP agent reads `sample_data/auth.log` with the official MCP Filesystem server, then sends the returned text to a custom Python MCP analysis server. No LLM or API key is used.

## Requirements

- Python 3.14 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Node.js and npm (provides `npx`), with internet access on the first run

The agent launches the published official `@modelcontextprotocol/server-filesystem` package from the [MCP servers repository](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem). It passes only this project's `sample_data/` directory as the server's allowed root.

## Run

From this directory:

```sh
uv sync
uv run python agent.py
```

The first run downloads the official Filesystem package through `npx`. The agent starts both MCP servers over stdio, reads `auth.log` through the Filesystem server, and invokes each analysis tool.

## Analysis tools

- `repeated_failed_logins`: username/IP pairs with at least 3 failures by default.
- `suspicious_ips`: IP addresses with at least 5 failures by default.
- `successful_logins`: successful authentication events.
- `assess_risk`: high for 5 or more failures, medium for 1-4, and low for none.

Input entries use whitespace-separated `key=value` fields, including `timestamp`, `user`, `ip`, and `status`. Malformed lines are ignored. This is a small demonstration heuristic, not a production security detection system.
