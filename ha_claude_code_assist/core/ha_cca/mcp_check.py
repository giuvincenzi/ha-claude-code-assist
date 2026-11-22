"""Checks that a configured MCP server answers, the way Claude Code connects to it.

Used after the panel saves the settings: for each HTTP server it sends `initialize`, then
`tools/list`, and reports the number of tools or an error a person can act on.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

PROTOCOL_VERSION = "2025-06-18"
TIMEOUT = 10  # seconds


def _post(url: str, headers: dict[str, str], message: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Sends one JSON-RPC message; returns the reply (JSON or the first SSE event) and the session id."""
    request = urllib.request.Request(
        url,
        data=json.dumps(message).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        session_id = response.headers.get("Mcp-Session-Id")
        body = response.read().decode()
    if not body.strip():
        return None, session_id
    if response.headers.get_content_type() == "text/event-stream":
        data = [line[5:].strip() for line in body.splitlines() if line.startswith("data:")]
        return (json.loads(data[0]) if data else None), session_id
    return json.loads(body), session_id


def check_server(config: dict[str, Any]) -> dict[str, Any]:
    """`{"ok": True, "tools": n}` or `{"ok": False, "error": "..."}`."""
    if config.get("type") != "http" or not config.get("url"):
        return {"ok": False, "error": 'Only HTTP servers are supported. Set "type" to "http" and add a "url".'}
    url = config["url"]
    headers = {str(k): str(v) for k, v in (config.get("headers") or {}).items()}
    try:
        init, session_id = _post(url, headers, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                       "clientInfo": {"name": "ha-claude-code-assist", "version": "1"}},
        })
        if not init or "result" not in init:
            return {"ok": False, "error": f"The server did not accept the connection. Its answer was {(init or {}).get('error')}."}
        headers = {**headers, "MCP-Protocol-Version": init["result"].get("protocolVersion", PROTOCOL_VERSION)}
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        _post(url, headers, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools, _ = _post(url, headers, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    except urllib.error.HTTPError as err:
        if err.code in (401, 403):
            return {"ok": False, "error": f"The server refused the token (HTTP {err.code}). Check the token in the headers."}
        if err.code == 404:
            return {"ok": False, "error": "Nothing was found at this address (HTTP 404). Check the url."}
        return {"ok": False, "error": f"The server answered with an error (HTTP {err.code})."}
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        reason = getattr(err, "reason", err)
        return {"ok": False, "error": f"The app cannot reach {url} ({reason})."}
    except (json.JSONDecodeError, KeyError, IndexError):
        return {"ok": False, "error": "The address answered, but not as an MCP server."}
    return {"ok": True, "tools": len(((tools or {}).get("result") or {}).get("tools") or [])}
