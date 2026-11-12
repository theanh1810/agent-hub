#!/usr/bin/env bash
# macOS only: reads its secret from the macOS Keychain (the security command).
set -euo pipefail
umask 077
# Launch @larksuiteoapi/lark-mcp@0.5.1 with its secret read from the Keychain item named by the first argument; remaining arguments go to the server.
if [ $# -lt 1 ] || [ -z "$1" ]; then
  echo "usage: lark.sh <keychain-service-name> [server arguments...]" >&2
  exit 2
fi
ITEM=$1
shift
if ! APP_SECRET="$(security find-generic-password -s "$ITEM" -a "$USER" -w 2>/dev/null)"; then
  echo "claude-mcp: Keychain item $ITEM not found; add it with security add-generic-password -U -s $ITEM -a \"\$USER\" -w" >&2
  exit 1
fi
export APP_SECRET
exec npx -y @larksuiteoapi/lark-mcp@0.5.1 "$@"
