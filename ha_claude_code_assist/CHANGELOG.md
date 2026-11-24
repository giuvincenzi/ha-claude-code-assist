# Changelog

## Unreleased

## 0.3.0

### Added

- Settings > Agent, where you rewrite the assistant's prompt, one for the chat of the panel and
  one for Home Assistant Assist, in five sections that each start from a default text.
- About, with the versions of the app, the integration and Claude Code, and links to the
  documentation, the changelog, the issues and the repository. When the app and the integration
  are not the same version, the panel shows Update needed and says which one to update, Assist
  says it too, and Home Assistant shows it in Repairs when the app is older.
- Sessions from Home Assistant show in Info what Home Assistant sent with each message.

### Changed

- Answers through Assist are shorter and written to be heard: one or two sentences with the
  essential details, a few words to confirm an action, and no links, sources or lists.
- Save and Discard stay in a bar at the bottom of Settings and Tools, and work only when
  something changed. In Settings they cover every tab, and a dot marks the tabs with changes
  not saved yet.
- The list of sessions shows where each one started, and a dot before its title when it is
  active or answering.
- Sessions from Assist are on the Home Assistant channel, instead of Voice, since they come
  from the Assist dialog too. Update the app and the integration together: the integration of
  0.2.0 cannot talk to this app.

### Fixed

- An answer to a question an automation asked with Start conversation on satellite now reaches
  the assistant together with the question, so it knows what you are answering.

## 0.2.0

### Changed

- A session now ends after 50 minutes without messages by default, instead of 5, so a
  conversation goes on after a pause. An app whose settings were already saved keeps its own
  timeout, which you can change in Settings > Sessions.

### Fixed

- Long memory entries go on several lines inside their box, instead of running off it and making
  the whole page scroll sideways.

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
