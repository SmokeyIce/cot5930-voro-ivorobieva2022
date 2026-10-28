"""Run the authentication-log workflow using two local MCP servers."""

import asyncio
import shutil
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = PROJECT_DIR / "sample_data"
LOG_PATH = SAMPLE_DIR / "auth.log"


def _text(result: object) -> str:
	"""Extract text content from an MCP tool result."""
	return "\n".join(item.text for item in result.content if hasattr(item, "text"))


async def main() -> None:
	"""Start both servers, read the sample, and run all analysis tools."""
	if not shutil.which("npx"):
		raise RuntimeError(
			"Node.js and npm are required for the official MCP Filesystem server. "
			"Install Node.js (which provides npx), then rerun: uv run python agent.py"
		)
	if not LOG_PATH.is_file():
		raise RuntimeError(f"Sample log not found: {LOG_PATH}")

	analyzer = StdioServerParameters(
		command=sys.executable,
		args=[str(PROJECT_DIR / "mcp-server.py")],
		cwd=str(PROJECT_DIR),
	)
	filesystem = StdioServerParameters(
		command="npx",
		args=["-y", "@modelcontextprotocol/server-filesystem", str(SAMPLE_DIR)],
		cwd=str(PROJECT_DIR),
	)

	async with (
		stdio_client(analyzer) as (analyzer_read, analyzer_write),
		ClientSession(analyzer_read, analyzer_write) as analyzer_session,
		stdio_client(filesystem) as (filesystem_read, filesystem_write),
		ClientSession(filesystem_read, filesystem_write) as filesystem_session,
	):
		await analyzer_session.initialize()
		await filesystem_session.initialize()
		read_result = await filesystem_session.call_tool(
			"read_file", {"path": str(LOG_PATH)}
		)
		if read_result.isError:
			raise RuntimeError(
				f"Filesystem server could not read sample log: {_text(read_result)}"
			)
		log_text = _text(read_result)
		if not log_text:
			raise RuntimeError("Filesystem server returned an empty sample log")

		print(f"Read sample log via Filesystem MCP: {LOG_PATH.name}\n")
		for tool_name in (
			"repeated_failed_logins",
			"suspicious_ips",
			"successful_logins",
			"assess_risk",
		):
			result = await analyzer_session.call_tool(
				tool_name, {"log_text": log_text}
			)
			if result.isError:
				raise RuntimeError(f"Analysis tool {tool_name} failed: {_text(result)}")
			print(f"{tool_name}:\n{_text(result)}\n")


if __name__ == "__main__":
	try:
		asyncio.run(main())
	except (OSError, RuntimeError) as error:
		print(f"Error: {error}", file=sys.stderr)
		raise SystemExit(1) from error
