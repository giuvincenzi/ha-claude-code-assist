"""Which client may reach which part of the core. No port is exposed outside the Supervisor's
internal network, and each part answers only its own client:

- the panel (everything else): the Supervisor's Ingress proxy, which signs the user in;
- the internal MCP server (/mcp): Claude Code, from inside the app;
- Assist (/api/assist): Home Assistant Core. It runs in the host's network, so its address is
  the host's: every request must also carry the token (assist.py).
"""

INGRESS_PROXY = "172.30.32.2"
HOME_ASSISTANT_CORE = "172.30.32.1"
LOCAL_HOSTS = frozenset({"127.0.0.1", "::1"})
MCP_PATH = "/mcp"
ASSIST_PATH = "/api/assist"


def _under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def allowed(path: str, host: str) -> bool:
    if _under(path, MCP_PATH):
        return host in LOCAL_HOSTS
    if _under(path, ASSIST_PATH):
        return host == HOME_ASSISTANT_CORE
    return host == INGRESS_PROXY
