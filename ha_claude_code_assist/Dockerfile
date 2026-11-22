# --- Panel (Lit + TypeScript, built with Vite) ---
FROM node:24.22.1-trixie-slim AS web

WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts
COPY web/ ./
RUN npm run build

# --- App ---
FROM ghcr.io/home-assistant/base-debian:trixie-2026.10.3 AS app

ARG BUILD_ARCH
ARG BUILD_VERSION
# Pinned: the stream-json events and the transcript format may change between versions.
ARG CLAUDE_CODE_VERSION=2.1.330

LABEL io.hass.type="app" \
      io.hass.arch="${BUILD_ARCH}" \
      io.hass.version="${BUILD_VERSION}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://claude.ai/install.sh | bash -s "${CLAUDE_CODE_VERSION}"
ENV PATH="/root/.local/bin:${PATH}"
RUN claude --version

COPY core/requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY core/ha_cca /opt/core/ha_cca
# The documentation is also what ha_cca_app_info gives Claude.
COPY DOCS.md /opt/docs/DOCS.md
COPY --from=web /web/dist /opt/web
COPY rootfs /

# --- Tests (`make test`): the app image plus test dependencies ---
FROM app AS test

COPY core/requirements-dev.txt /tmp/requirements-dev.txt
RUN /opt/venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements-dev.txt \
    && rm /tmp/requirements-dev.txt

# --- Final image (built by the Supervisor) ---
FROM app
