---
paths:
  - "Makefile"
  - "compose.yaml"
  - "tools/**"
  - "scripts/**"
  - ".env.example"
  - "ha_claude_code_assist/core/requirements*"
  - "ha_claude_code_assist/web/package*.json"
  - "integration-tests/requirements*"
---

# Development environment

The Makefile, the containers and the test Home Assistant.

- The Makefile is the only entry point; `scripts/` holds what it runs. Nothing is installed on the
  host: every tool runs in a container.
- Every container is a service of `compose.yaml` (Compose project `ha-claude-code-assist`), so
  Docker shows them grouped; short-lived tools are in the `tools` profile.
- The test environment (`dev`) is the official apps devcontainer image, pinned by digest, plus
  two systemd services (`tools/dev/`): it provisions itself at every start (onboarding with the
  user from `.env`, the app with the token from `.env`), so Start in Docker Desktop is enough.
- The test environment is privileged and shares the host's kernel: nothing in it may change
  kernel-wide state. `systemd-binfmt` is masked in `tools/dev/Dockerfile`: it cleared the host's
  binfmt rules, WSL's interop with Windows programs included.
- At every start the test Home Assistant gets the Assist integration from the repository
  (`ha-dev-config`), set up from discovery and made the voice assistant's agent (`ha-dev-setup`).
  `make integration-sync` copies it again after a change and restarts Home Assistant Core.
- Its data is clean at every start (`/mnt/supervisor` is a tmpfs, made a shared mount for Home
  Assistant); image caches are volumes. The production Home Assistant is never used for tests.
- New Home Assistant installations listen on port 80, not 8123: the test environment maps
  `127.0.0.1:7123` to 80.
- Versions are pinned and locked (`make lock`: hashed requirements, `package-lock.json`); a new
  version is one published at least two weeks earlier.
