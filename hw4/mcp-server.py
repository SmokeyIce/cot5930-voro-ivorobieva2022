"""MCP tools for basic authentication-log analysis."""

import json
import shlex
from collections import Counter

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("authentication-log-analysis")


def _events(log_text: str) -> list[dict[str, str]]:
	"""Parse whitespace-separated key=value authentication log entries."""
	events = []
	for line in log_text.splitlines():
		try:
			fields = dict(
				token.split("=", 1)
				for token in shlex.split(line)
				if "=" in token
			)
		except ValueError:
			continue
		status = fields.get("status", fields.get("result", "")).lower()
		if status in {"failed", "failure", "success", "succeeded"}:
			events.append(
				{
					"timestamp": fields.get("timestamp", ""),
					"username": fields.get("user", fields.get("username", "unknown")),
					"ip": fields.get("ip", fields.get("source_ip", "unknown")),
					"status": "failed" if status in {"failed", "failure"} else "success",
				}
			)
	return events


def _json(data: object) -> str:
	"""Return stable, readable JSON for MCP clients."""
	return json.dumps(data, indent=2, sort_keys=True)


@mcp.tool()
def repeated_failed_logins(log_text: str, threshold: int = 3) -> str:
	"""List username/IP pairs with at least threshold failed logins (default 3)."""
	if threshold < 1:
		return _json({"error": "threshold must be at least 1"})
	counts: Counter[tuple[str, str]] = Counter(
		(event["username"], event["ip"])
		for event in _events(log_text)
		if event["status"] == "failed"
	)
	return _json(
		[
			{"username": username, "ip": ip, "failed_attempts": count}
			for (username, ip), count in sorted(counts.items())
			if count >= threshold
		]
	)


@mcp.tool()
def suspicious_ips(log_text: str, threshold: int = 5) -> str:
	"""List IPs with at least threshold failed logins (default 5)."""
	if threshold < 1:
		return _json({"error": "threshold must be at least 1"})
	counts = Counter(
		event["ip"]
		for event in _events(log_text)
		if event["status"] == "failed"
	)
	return _json(
		[
			{"ip": ip, "failed_attempts": count}
			for ip, count in sorted(counts.items())
			if count >= threshold
		]
	)


@mcp.tool()
def successful_logins(log_text: str) -> str:
	"""List successful authentication events found in the supplied log text."""
	return _json(
		[event for event in _events(log_text) if event["status"] == "success"]
	)


@mcp.tool()
def assess_risk(log_text: str) -> str:
	"""Assign high risk for 5+ failures, medium for 1-4, and low for none."""
	failed = sum(event["status"] == "failed" for event in _events(log_text))
	level = "high" if failed >= 5 else "medium" if failed else "low"
	return _json({"risk_level": level, "failed_login_count": failed})


if __name__ == "__main__":
	mcp.run(transport="stdio")
