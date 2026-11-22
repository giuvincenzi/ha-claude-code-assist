---
paths:
  - "README.md"
  - "repository.yaml"
  - "ha_claude_code_assist/README.md"
  - "ha_claude_code_assist/DOCS.md"
  - "ha_claude_code_assist/CHANGELOG.md"
  - "ha_claude_code_assist/config.yaml"
  - "ha_claude_code_assist/translations/**"
  - "ha_claude_code_assist/core/ha_cca/config.py"
  - "ha_claude_code_assist/core/ha_cca/sessions.py"
  - "ha_claude_code_assist/core/ha_cca/memory.py"
  - "ha_claude_code_assist/core/ha_cca/panel.py"
  - "ha_claude_code_assist/core/ha_cca/mcp_check.py"
  - "ha_claude_code_assist/core/ha_cca/claude_process.py"
  - "ha_claude_code_assist/web/src/**"
  - "custom_components/**"
  - "hacs.json"
---

# Documentation and texts

The README files, the user documentation and the changelog, laid out as in every Home Assistant
app repository, and how every text the user reads is written.

- Every text the user reads (labels, hints, badges, tooltips, dialogs, errors from the panel,
  the core or the integration, what Assist says, the Configuration tab, `DOCS.md`) is a natural
  sentence, the way a person would say it: what it is or what happened, and what the user can do
  next. No pieces glued with colons, semicolons or symbols (`·`, `/`), no shorthand, no internal
  names (option keys, field names). Short where space is short, but still a sentence. The only
  `·` is between the name and the time above a chat message. Texts written for Claude (prompt,
  tool descriptions and errors) are not covered.
- The same thing has one name everywhere: a conversation with the assistant is a "session"
  (tab, buttons, settings, documentation); the subscription token is the "setup token".
- The name shown everywhere is "HA Claude Code Assist", matching the repository
  `ha-claude-code-assist` and the slug `ha_claude_code_assist`.
- One description, the same words everywhere: the one-line description (`config.yaml`
  `description`, the `README.md` subtitle) and the paragraph that opens both README files and
  `DOCS.md`. Changing it changes every copy in the same change.
- Every page that presents the app says it is unofficial and not affiliated with Anthropic, and
  never presents it as made or endorsed by Anthropic ("powered by", "official").
- `README.md` (repository) is short: name, one line, the paragraph, then Documentation,
  Feedback, Development (`.claude/rules/`) and License. It never repeats the documentation.
- `ha_claude_code_assist/README.md` is the app's presentation in the Home Assistant app store: the
  paragraph only.
- `ha_claude_code_assist/DOCS.md` is the only user documentation: Home Assistant shows it in the
  app's Documentation tab, and `ha_cca_app_info` gives it to Claude. No other documentation file.
- It is written for people who use the app: plain words, short sections with bullets, the labels
  the panel and Home Assistant show (checked in Home Assistant's own English texts); no code names
  except what the user types (settings, JSON, formatted on several lines).
- Describe only what the code does: check the code before writing about behaviour, defaults or
  limits. What is not built yet is said to be planned, never described as available.
- A change to what the user sees or does (a setting, a panel tab, sessions, memory, tools)
  updates `DOCS.md` in the same change, `translations/en.yaml` when a setting changes, and adds a
  line to `ha_claude_code_assist/CHANGELOG.md` under the version being prepared.
