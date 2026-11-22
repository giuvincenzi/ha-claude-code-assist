---
paths:
  - "ha_claude_code_assist/core/**"
  - "ha_claude_code_assist/web/**"
  - "scripts/**"
  - "custom_components/**"
  - "integration-tests/**"
  - ".github/workflows/test.yml"
  - "ruff.toml"
---

# Tests

Which tests exist and when they run.

- `make test`: the core's automated tests (`core/tests/`, pytest), in the app image itself so
  Python, packages and git are the production ones, and the release script's
  (`scripts/*.test.mjs`, `node --test`). Session rules are tested with a fake Claude Code process.
- `make test-integration`: the Assist integration's tests (`integration-tests/`), with
  `pytest-homeassistant-custom-component`, which pins the Home Assistant version they run on.
  The app is faked at the HTTP level. Run before every commit that touches `custom_components/`.
- `make lint`: the Python (ruff with its default rules, `ruff.toml`), the panel's TypeScript types
  and ESLint. A finding is fixed in the code, never silenced by turning its rule off.
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
- On GitHub, `test.yml` runs lint, `make test`, `make test-integration` and the app's build on
  amd64 and aarch64 machines, on every pull request and push to `main`. The required checks are
  `unit_test` (lint and tests) and `build_test` (the build).
- `decide_which_tests_run` skips the checks a change cannot affect, from the files each one reads:
  a check that starts reading another file gets it in its pattern in the same pull request. Never
  filter the workflow with `paths`: a workflow that does not start leaves a required check pending.
- The end-to-end tests (`make app-smoke`) need the test environment and a real Claude Code token,
  so they run only locally: before the merge of a pull request that changes the app or the
  integration, and of every release pull request.
- A failing test is a bug until proven otherwise: fix the code, not the test.
