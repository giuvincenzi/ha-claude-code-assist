---
paths:
  - "ha_claude_code_assist/core/**"
  - "ha_claude_code_assist/Dockerfile"
  - "ha_claude_code_assist/config.yaml"
  - "ha_claude_code_assist/rootfs/**"
  - "custom_components/**"
---

# Architecture

How the app and its core are organized.

- The core (`core/ha_cca/`) is one Python process (FastAPI on uvicorn, started by S6 in
  `rootfs/`): the panel's HTTP and WebSocket, the session manager and the internal MCP server.
- The core only orchestrates Claude Code: it never calls the Anthropic API itself and never
  restricts the user's MCP tools. What a server exposes is up to whoever configures it.
- Claude Code runs headless (`launch.py`, `claude_process.py`): no built-in tools except Read
  (read files) and WebSearch and WebFetch (web search), only the configured MCP servers plus
  `ha_cca` (`--strict-mcp-config`), `dontAsk` with every configured server allowed.
- Read is never an allowed tool (an allow rule would let it read anywhere). Claude Code lets it
  read only the working directory and its own files of the session, and
  `blockReadsOutsideWorkingDirectories` refuses the rest. Each session has its own working
  directory, so it never reaches another session. Reading its own project folder is not
  documented: the smoke test checks the isolation, and a new Claude Code version is pinned only
  when it passes.
- Attached files go over HTTP (`attachment_routes.py`), one request each, never over the panel's
  WebSocket: a large upload would hold up the answers streaming on it. Home Assistant's Ingress
  refuses bodies over 16 MiB, so the panel checks the size before sending.
- An attached file never runs as a page of Home Assistant's origin (an HTML or SVG file would):
  only pictures (PNG, JPEG, GIF, WebP) are served to be shown; any other file only as a download
  (`Content-Disposition: attachment`); always with `nosniff` and a sandbox policy.
- `--bare` cannot be used: it ignores the subscription token. `ANTHROPIC_API_KEY` is removed
  from Claude Code's environment, or it would bill the API instead of the subscription.
- The internal MCP server is mounted at `/mcp` in the same app. Its tools are named `ha_cca_*`
  and raise `ToolError` with a message that says what happened and what to do: any other
  exception reaches the model as a bare "Error executing tool".
- Connections (`access.py`): the panel only from the Ingress proxy (`172.30.32.2`), `/mcp` only
  from the app itself, `/api/assist` only from Home Assistant Core (`172.30.32.1`). No port is
  exposed.
- Home Assistant Core runs in the host's network: its requests come from the same address as any
  process of the host, so the address proves nothing. `/api/assist` also needs the token the core
  creates (`AssistToken`, in `/data`).
- Assist goes through a thin integration in the same repository (`custom_components/`, installed
  from the Marketplace, or HACS before Home Assistant 2026.11, both reading `hacs.json`): an app
  cannot be a conversation agent. It only relays sentences and answers; the sessions, the tools
  and Claude Code stay in the core.
- The integration learns the address and the token from Supervisor discovery (`config.yaml`
  `discovery`), which the core announces at every start: a new token reaches it by itself. There
  is no setup or new token by hand (`config_flow.py`): the token is shown nowhere.
- Options are the app's Supervisor options (`config.yaml` schema). The panel saves them through
  the Supervisor API with the complete options, and the core keeps them in memory: the
  Supervisor rewrites `/data/options.json` only at the next start.
- No logs of our own: Claude Code's transcripts are the history, shown by the panel
  (`transcripts.py`). Their format is internal to Claude Code: the CLI version is pinned in the
  Dockerfile and a new version is tested before it is pinned.
- A new dependency (Python or npm) needs the owner's approval.
