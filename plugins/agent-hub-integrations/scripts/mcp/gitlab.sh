#!/usr/bin/env bash
# macOS only: reads its secret from the macOS Keychain (the security command).
set -euo pipefail
umask 077
# Launch @zereight/mcp-gitlab@2.1.0 with its secret read from the Keychain item named by the first argument; remaining arguments go to the server.
if [ $# -lt 1 ] || [ -z "$1" ]; then
  echo "usage: gitlab.sh <keychain-service-name> [server arguments...]" >&2
  exit 2
fi
ITEM=$1
shift
if ! GITLAB_PERSONAL_ACCESS_TOKEN="$(security find-generic-password -s "$ITEM" -a "$USER" -w 2>/dev/null)"; then
  echo "claude-mcp: Keychain item $ITEM not found; add it with security add-generic-password -U -s $ITEM -a \"\$USER\" -w" >&2
  exit 1
fi
export GITLAB_PERSONAL_ACCESS_TOKEN
exec npx -y @zereight/mcp-gitlab@2.1.0 "$@"
