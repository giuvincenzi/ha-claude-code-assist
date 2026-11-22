---
paths:
  - "ha_claude_code_assist/core/**"
  - "ha_claude_code_assist/web/**"
  - "scripts/**"
  - "custom_components/**"
  - "integration-tests/**"
---

# Tests

Which tests exist and when they run.

- `make test`: the core's automated tests (`core/tests/`, pytest), in the app image itself so
  Python, packages and git are the production ones. Session rules are tested with a fake Claude
  Code process. Run before every commit.
- `make test-integration`: the Assist integration's tests (`integration-tests/`), with
  `pytest-homeassistant-custom-component`, which pins the Home Assistant version they run on.
  The app is faked at the HTTP level. Run before every commit that touches `custom_components/`.
- `make lint`: the panel's TypeScript types and ESLint. Run before every commit that touches
  `web/`.
- `make app-smoke`: end to end through Ingress, as the browser does: login, panel, WebSocket,
  settings saved through the Supervisor, a real chat with Claude, memory, resume after an app
  restart, transcripts, Read refusing another session's files and the app's own, an image from
  the web opened, attachments, a rejected token, and Assist through the voice assistant
  (`assist_pipeline/run`, as the Assist dialog) and the integration set up from discovery. Run
  after every change to the app, with the test environment up.
- `make app-behave`: real conversations from `scripts/app-behave.json`, reported with answers,
  tools, model turns and times. It checks nothing by itself: it is read before and after a change
  to the prompt or to a tool. It changes settings and memory of the test environment and restores
  them at the end: nobody else uses the panel while it runs.
- The tests never use the MCP servers configured in the panel: they can point to a real home,
  and `app-behave` turns lights off and changes thermostats. `app-smoke` and `app-behave` use
  only the test Home Assistant's own MCP Server (`testMcpServers` in `scripts/panel-client.mjs`)
  and put the configured servers back at the end.
- A failing test is a bug until proven otherwise: fix the code, not the test.
