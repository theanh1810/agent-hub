#!/usr/bin/env bash
# macOS only: reads its secret from the macOS Keychain (the security command).
set -euo pipefail
umask 077
# Launch figma-developer-mcp@0.10.1 with its secret read from the Keychain item named by the first argument; remaining arguments go to the server.
if [ $# -lt 1 ] || [ -z "$1" ]; then
  echo "usage: figma.sh <keychain-service-name> [server arguments...]" >&2
  exit 2
fi
ITEM=$1
shift
cd "$(dirname "$0")"
if [ -e .env ]; then
  echo "claude-mcp: a .env file sits in $(pwd); figma-developer-mcp would load it over the Keychain key; remove it" >&2
  exit 1
fi
if ! FIGMA_API_KEY="$(security find-generic-password -s "$ITEM" -a "$USER" -w 2>/dev/null)"; then
  echo "claude-mcp: Keychain item $ITEM not found; add it with security add-generic-password -U -s $ITEM -a \"\$USER\" -w" >&2
  exit 1
fi
export FIGMA_API_KEY
exec npx -y figma-developer-mcp@0.10.1 "$@"
