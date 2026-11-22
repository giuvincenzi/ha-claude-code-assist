# Test environment: the official apps devcontainer image (Supervisor and Home
# Assistant in Docker-in-Docker), plus two systemd services so that the
# container is ready on its own when it starts:
# - ha-supervisor: writes the test configuration, then runs the image's own
#   supervisor_run script;
# - ha-dev-setup: onboarding, Home Assistant's MCP Server, then the app from
#   the local folder with its token.
FROM ghcr.io/home-assistant/devcontainer:6-apps@sha256:9c08de75a4d91938dab76d44846a2d297d4ce92bf80024ff15a4f6dff766855e

# Python for the WebSocket commands of ha-dev-ws.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-websockets \
    && rm -rf /var/lib/apt/lists/*

COPY ha-supervisor.service ha-dev-setup.service /etc/systemd/system/
COPY ha-dev-config ha-dev-setup ha-dev-ws /usr/local/bin/

# The container is privileged and shares the host's kernel: systemd-binfmt would
# clear the host's binfmt rules (WSL's interop with Windows programs among them)
# as soon as any package installs a rule of its own. It never runs here.
RUN chmod 0755 /usr/local/bin/ha-dev-config /usr/local/bin/ha-dev-setup /usr/local/bin/ha-dev-ws \
    && systemctl enable ha-supervisor.service ha-dev-setup.service \
    && systemctl mask systemd-binfmt.service proc-sys-fs-binfmt_misc.automount proc-sys-fs-binfmt_misc.mount
