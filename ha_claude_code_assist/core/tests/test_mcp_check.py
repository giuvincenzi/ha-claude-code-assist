import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ha_cca.mcp_check import check_server

TOKEN = "Bearer right"


class FakeMcpServer(BaseHTTPRequestHandler):
    """Answers like an MCP server over HTTP: JSON for initialize, SSE for tools/list."""

    def do_POST(self):  # noqa: N802 (http.server API)
        message = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.headers.get("Authorization") != TOKEN:
            self.send_response(401)
            self.end_headers()
            return
        if message["method"] == "initialize":
            body, content_type = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-06-18"}}), "application/json"
        elif message["method"] == "tools/list":
            assert self.headers["Mcp-Session-Id"] == "abc"
            result = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "a"}, {"name": "b"}]}}
            body, content_type = f"event: message\ndata: {json.dumps(result)}\n\n", "text/event-stream"
        else:
            self.send_response(202)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Mcp-Session-Id", "abc")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeMcpServer)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/mcp"
    server.shutdown()


def test_connected_server_reports_its_tools(url):
    assert check_server({"type": "http", "url": url, "headers": {"Authorization": TOKEN}}) == {"ok": True, "tools": 2}


def test_wrong_token(url):
    result = check_server({"type": "http", "url": url, "headers": {"Authorization": "Bearer wrong"}})
    assert result == {"ok": False, "error": "The server refused the token (HTTP 401). Check the token in the headers."}


def test_unreachable_address():
    result = check_server({"type": "http", "url": "http://127.0.0.1:1/mcp"})
    assert not result["ok"] and result["error"].startswith("The app cannot reach http://127.0.0.1:1/mcp")


def test_only_http_servers():
    assert not check_server({"type": "stdio", "command": "x"})["ok"]
