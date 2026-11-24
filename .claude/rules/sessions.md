---
paths:
  - "ha_claude_code_assist/core/ha_cca/sessions.py"
  - "ha_claude_code_assist/core/ha_cca/claude_process.py"
  - "ha_claude_code_assist/core/ha_cca/launch.py"
  - "ha_claude_code_assist/core/ha_cca/panel.py"
  - "ha_claude_code_assist/core/ha_cca/assist.py"
  - "custom_components/ha_claude_code_assist/conversation.py"
---

# Sessions

How conversations map to Claude Code sessions and processes (`sessions.py`).

- A session has two ids, each used only for what it is: ours (`session_id`, created before
  Claude Code starts: record, folder, panel, memory, the `ha_cca` header, `--session-id` of a
  new conversation) and Claude Code's (`claude.session_id`, as its init event reports it:
  `--resume`, the transcript's name). Several channel conversation ids can be attached.
- A message goes to the session of its conversation id; otherwise to the active session of its
  source (channel and source key), attaching the id; otherwise to a new session.
- A session is active while it had a turn within the conversation timeout. Its default (50
  minutes) keeps a session inside Claude Code's prompt cache, which lasts an hour from its last use
  (`ephemeral_1h_input_tokens` in the transcripts), with room for a long turn.
- One turn at a time per session, others wait; different sessions run in parallel.
- One process per session, started on demand, always in the session's own working directory
  (`/data/sessions/<session_id>/workdir/`): `--resume <claude.session_id>` when its transcript
  exists, `--session-id <session_id>` otherwise. There is no spare process.
- A session keeps the settings it was created with (model, effort, web search, read files,
  memory). MCP servers are not fixed: a resumed process gets the configured ones, and
  `settings.mcp_servers` names those of its last start.
- Deleting a session is refused while a turn runs or waits: it holds the session's turn lock, so
  a message sent meanwhile finds the session closed and starts a new one. The record goes
  last, so an interrupted deletion is finished by the next one.
- A session with no messages for longer than `session_retention_days` is deleted by the core,
  as Delete does (`remove_expired`: at start, every hour, when the setting changes). Claude
  Code's own cleanup (`cleanupPeriodDays`) is set a day later, because it does not document
  which date it counts from: it never removes the messages of a session still listed.
- The panel's source key is the Home Assistant user; it generates its own conversation id per
  chat thread, and "New session" closes the current session first.
- Assist's channel is `home_assistant` (`voice` before 0.3.0, renamed when a record is read:
  `RENAMED_CHANNELS`); its source key is the voice satellite, else the voice device, else the
  user who spoke (`_source` in the integration's `conversation.py`), so each device keeps its own
  session. Home Assistant's conversation id is attached as the panel's ids are.
- What Home Assistant sent with a message is kept under the turn lock (`run`), in the session
  that gets the message, which is a new one when the session closed while it waited.
- A voice turn goes on when Home Assistant stops listening (`stream_turn`): cancelling it would
  leave the session's transcript cut in the middle of a tool call.
