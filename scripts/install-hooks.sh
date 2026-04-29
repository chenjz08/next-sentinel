#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-"$HOME/.codex"}"
HOOKS_DIR="${NEXT_HOOKS_DIR:-"$CODEX_HOME/hooks"}"

mkdir -p "$HOOKS_DIR"
install -m 0755 "$ROOT/hooks/next_ctl.py" "$HOOKS_DIR/next_ctl.py"
install -m 0755 "$ROOT/hooks/next_session_start.py" "$HOOKS_DIR/next_session_start.py"
install -m 0755 "$ROOT/hooks/next_stop_router.py" "$HOOKS_DIR/next_stop_router.py"

if [ ! -f "$HOOKS_DIR/next_router_config.json" ]; then
  install -m 0644 "$ROOT/examples/next_router_config.example.json" "$HOOKS_DIR/next_router_config.json"
fi

cat <<EOF
hooks installed to: $HOOKS_DIR

Next steps:
1. Edit $HOOKS_DIR/next_router_config.json.
2. Merge examples/config.toml.snippet into $CODEX_HOME/config.toml.
3. Create automation-2 from examples/automation-2.toml in $CODEX_HOME/automations/automation-2/automation.toml.
4. Run:
   python3 $HOOKS_DIR/next_ctl.py status
EOF
