#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Install FL-Agent on macOS.
#
# Usage: scripts/install.sh [--no-plugins] [--controller-only]
#   --no-plugins       skip building the FL-Agent FX / instrument plugins
#   --controller-only  only (re)install the FL Studio controller and Piano Roll
#                      scripts (use after editing fl_controller/; restart FL after)
#
# Steps (each is safe to re-run):
# 1. Check prerequisites.
# 2. Install the MCP server's Python environment (uv sync).
# 3. Copy the controller and Piano Roll scripts into FL Studio's settings folder.
# 4. Build and install the plugins and the renderer (scripts/build-plugins.sh).
# 5. Register the MCP server with Claude Code, if the claude CLI is available.
# Then print the manual FL Studio steps (see docs/getting-started.md).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER="$ROOT/fl-studio-mcp"
FL_SETTINGS="$HOME/Documents/Image-Line/FL Studio/Settings"
MCP_NAME="fl-studio"

plugins=true
controller_only=false
for arg in "$@"; do
  case "$arg" in
    --no-plugins) plugins=false ;;
    --controller-only) controller_only=true ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

log() { printf '==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

install_fl_scripts() {
  [ -d "$FL_SETTINGS" ] || fail "FL Studio settings not found at $FL_SETTINGS (install and start FL Studio once first)"
  mkdir -p "$FL_SETTINGS/Hardware/FLStudioMCP" "$FL_SETTINGS/Piano roll scripts"
  cp "$SERVER/fl_controller/device_FLStudioMCP.py" "$FL_SETTINGS/Hardware/FLStudioMCP/"
  cp "$SERVER/scripts/ComposeWithLLM.pyscript" "$FL_SETTINGS/Piano roll scripts/"
  log "Installed the controller and Piano Roll scripts (restart FL Studio to load changes)"
}

# 1. Prerequisites
[ "$(uname -s)" = "Darwin" ] || fail "FL-Agent's install script supports macOS only"
if $controller_only; then
  install_fl_scripts
  exit 0
fi
command -v uv >/dev/null || fail "uv not found: https://docs.astral.sh/uv/ (brew install uv)"
ls /Applications | grep -q "^FL Studio" || warn "FL Studio not found in /Applications"

# 2. Python environment
log "Installing the MCP server's Python environment"
(cd "$SERVER" && uv sync --quiet)

# 3. FL Studio scripts
install_fl_scripts

# 4. Plugins
if $plugins; then
  "$ROOT/scripts/build-plugins.sh"
else
  log "Skipping plugins (--no-plugins); custom DSP tools won't work until you build them"
fi

# 5. Claude Code registration
if command -v claude >/dev/null; then
  if claude mcp get "$MCP_NAME" >/dev/null 2>&1; then
    log "MCP server '$MCP_NAME' is already registered with Claude Code"
  else
    claude mcp add --scope user "$MCP_NAME" -- uv run --directory "$SERVER" fl-studio-mcp
    log "Registered MCP server '$MCP_NAME' with Claude Code"
  fi
else
  warn "claude CLI not on PATH. Register the server yourself:"
  printf '    claude mcp add --scope user %s -- uv run --directory "%s" fl-studio-mcp\n' "$MCP_NAME" "$SERVER"
fi

cat <<EOF

Installed. Finish setup in FL Studio (details: docs/getting-started.md):
  1. Audio MIDI Setup > Window > Show MIDI Studio > IAC Driver > "Device is online" > Apply
  2. Restart FL Studio. Options > MIDI settings > Input: select "IAC Driver Bus 1",
     set Controller type to "FL Studio MCP Controller", enable it
  3. Options > Manage plugins > Find installed plugins (finds FL-Agent FX / instrument)
  4. Optional: create the FL-Agent template (docs/getting-started.md#project-template)
  5. Start a new Claude Code session and ask it to check the FL Studio connection
EOF
