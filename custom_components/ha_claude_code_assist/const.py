"""Constants of the HA Claude Code Assist integration."""

DOMAIN = "ha_claude_code_assist"

# Every request carries the integration's version, every answer the app's: both come from the
# same release, and the app's panel and this integration say which one to update when they differ.
INTEGRATION_VERSION_HEADER = "X-HA-CCA-Integration-Version"
APP_VERSION_HEADER = "X-HA-CCA-App-Version"

# The Repairs issue raised while the app is older than this integration.
APP_OUTDATED_ISSUE = "app_outdated"
