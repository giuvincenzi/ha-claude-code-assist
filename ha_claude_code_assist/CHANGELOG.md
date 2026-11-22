# Changelog

## Unreleased

## 0.1.0

### Added

- The HA Claude Code Assist panel with Chat, Memory, Tools, Sessions and Settings. Answers are
  shown as they are written, formatted with lists, tables, code and links, together with the
  tools the assistant uses.
- Tools from any MCP server, such as Home Assistant's own MCP Server, checked when saved,
  optional web search, and file reading limited to each session's own files, so the assistant
  can look at images it finds on the web.
- Sessions that end after a timeout and continue after an app restart. Each one shows the
  tokens it used and how full its context is, and can be deleted. Old sessions are deleted
  after the number of days you choose.
- Files attached to a message (pasted, dropped anywhere on the chat or chosen), up to 16 MB
  each, which the assistant opens itself. Pictures open over the page, and any file can be
  downloaded.
- Long-term memory, saved only on request and editable in the panel.
- Voice through Home Assistant Assist, with the HA Claude Code Assist integration installed from
  the Marketplace or HACS. Home Assistant finds the app by itself, and each voice assistant
  device has its own session.
- Every setting in the panel and in the app's Configuration tab.
- An icon for the app and for the integration.
- The chat and the panel's status say when the setup token is missing, rejected or about to
  expire.
