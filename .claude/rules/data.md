---
paths:
  - "ha_claude_code_assist/core/ha_cca/sessions.py"
  - "ha_claude_code_assist/core/ha_cca/memory.py"
  - "ha_claude_code_assist/core/ha_cca/config.py"
  - "ha_claude_code_assist/core/ha_cca/app.py"
  - "ha_claude_code_assist/core/ha_cca/transcripts.py"
  - "ha_claude_code_assist/core/ha_cca/attachments.py"
---

# Data

What the app keeps in `/data` and how it stays compatible between versions.

- `/data` holds: `options.json` (Supervisor), `token.json` (when the current token was first
  seen, for its expiry), `memory/` (`memory.json` in a git repository), `sessions/` and
  `claude/` (Claude Code's own state and transcripts; the core never writes there).
- `sessions/<session_id>/` holds the record (`session.json`) and `workdir/`, the session's
  working directory with the attached files in `attachments/`. Claude Code reads only
  `workdir/`, so the record stays outside it.
- A message tells Claude about an attached file with the line `[Attached file: <path>]`, our own
  convention (`attachments.py`): the history recognises it only at the end of a user message and
  only for the session's own attachments. Changing it changes both sides and their tests.
- The core writes its files atomically (temporary file, then rename).
- `session.json` keeps only what the panel shows, in three parts: the app's own fields,
  `settings` (never secrets: the record reaches the browser) and `claude` (what Claude Code
  reports). Anything else is read from Claude Code's transcript when needed.
- Deleting a session removes `sessions/<session_id>/` and its Claude Code project folder
  (`Transcripts.remove_project`, named after the working directory): both found from our id.
  Memory entries keep their `conversation_id`.
- `memory.json` is written only through `MemoryStore`, which commits every change. Memory ids are
  never reused (`next_id`), so an id quoted in an old conversation never points to another entry.
- A new version must read the files an older one wrote: a new field gets a default, and a change
  of format comes with a migration and its test.
