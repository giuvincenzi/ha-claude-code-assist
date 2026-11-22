#!/usr/bin/env bash
# Waits until the test environment has provisioned itself (ha-dev-setup).
set -euo pipefail

DEV_CONTAINER="${DEV_CONTAINER:-ha-claude-code-assist-dev}"
TIMEOUT="${TIMEOUT:-1800}"

for ((elapsed = 0; elapsed < TIMEOUT; elapsed += 5)); do
    state="$(docker exec "${DEV_CONTAINER}" systemctl is-active ha-dev-setup 2>/dev/null || true)"
    case "${state}" in
        active)
            echo "Test environment ready (${elapsed}s): http://localhost:7123"
            exit 0
            ;;
        failed)
            docker exec "${DEV_CONTAINER}" journalctl -u ha-dev-setup --no-pager -n 30 >&2
            exit 1
            ;;
    esac
    sleep 5
done
echo "Test environment not ready within ${TIMEOUT}s" >&2
exit 1
