#!/usr/bin/env bash
set -euo pipefail

CODEX_BUNDLE_ID="${CODEX_BUNDLE_ID:-com.openai.codex}"
SENTINEL_APP="${SENTINEL_APP:-$HOME/Applications/Next Sentinel.app}"

if [ -d "$SENTINEL_APP" ]; then
  open "$SENTINEL_APP"
fi

osascript -e "tell application id \"$CODEX_BUNDLE_ID\" to quit" >/dev/null 2>&1 || true

for _ in $(seq 1 30); do
  if ! pgrep -f "$CODEX_BUNDLE_ID" >/dev/null 2>&1 && ! pgrep -x "Codex" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

open -b "$CODEX_BUNDLE_ID"

cat <<EOF
Codex restarted.
If Next Sentinel is running, it will detect Codex startup and trigger the one-shot fallback after its delay.
EOF
