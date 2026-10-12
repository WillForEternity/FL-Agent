#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Build and install the FL-Agent FX / FL-Agent instrument plugins (modified ysfx),
# plus flagent_render, the offline JSFX checker (installed to FL-Agent/bin).
#
# Usage: scripts/build-plugins.sh [--clean] [--no-install]
#   --clean       delete the build directory and reconfigure (downloads JUCE again)
#   --no-install  build and verify only
#
# Steps:
# 0. Fetch ysfx (upstream, pinned commit) into vendor/ysfx and apply
#    patches/ysfx-flagent.patch, unless a matching checkout is already there.
# 1. Pick a macOS SDK the installed linker can actually link against. The
#    Command Line Tools 26.6 default to a 27.0 SDK that their linker rejects.
# 2. Configure (first run only) and build both VST3 targets.
# 3. Verify each binary contains the FL-Agent changes and has a valid signature.
# 4. Install into ~/Library/Audio/Plug-Ins/VST3 by atomic swap, so a running
#    FL Studio keeps using the old file until it restarts.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
YSFX="${FLAGENT_YSFX_DIR:-$ROOT/vendor/ysfx}"   # override to build elsewhere (e.g. a clean-checkout test)
YSFX_REPO="https://github.com/JoepVanlier/ysfx.git"
YSFX_COMMIT="5c3452fee62583aa3d1b7e877d0c758c4024af89"
PATCH="$ROOT/patches/ysfx-flagent.patch"
BUILD="$YSFX/build"
DEST="$HOME/Library/Audio/Plug-Ins/VST3"
SDK_DIR="/Library/Developer/CommandLineTools/SDKs"
TARGETS=(ysfx_plugin_VST3 ysfx_plugin_instrument_VST3 flagent_render)
RENDER_BIN="$ROOT/bin/flagent_render"
SMOKE_SCRIPT="$ROOT/dsp/petal-delay.jsfx"
BUNDLES=(
  "ysfx_plugin_artefacts/Release/VST3/FL-Agent FX.vst3"
  "ysfx_plugin_instrument_artefacts/Release/VST3/FL-Agent instrument.vst3"
)
# Strings that must be in the binaries (one per FL-Agent feature)
MARKERS=("pending.txt" "flagent_assign")

clean=false
install=true
for arg in "$@"; do
  case "$arg" in
    --clean) clean=true ;;
    --no-install) install=false ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

log() { printf '==> %s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# 1. SDK: newest versioned SDK that links a trivial program
pick_sdk() {
  local tmp sdk
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN
  printf 'int main(void){return 0;}\n' > "$tmp/t.c"
  for sdk in $(ls -d "$SDK_DIR"/MacOSX[0-9]*.[0-9]*.sdk 2>/dev/null | sort -V -r); do
    if SDKROOT="$sdk" cc "$tmp/t.c" -o "$tmp/t" 2>/dev/null; then
      echo "$sdk"
      return 0
    fi
  done
  return 1
}

command -v cmake >/dev/null || fail "cmake not found (brew install cmake)"
command -v git >/dev/null || fail "git not found (xcode-select --install)"

# 0. ysfx source: pinned upstream + our patch
if [ ! -d "$YSFX/.git" ]; then
  log "Fetching ysfx $YSFX_COMMIT"
  mkdir -p "$(dirname "$YSFX")"
  git clone -q "$YSFX_REPO" "$YSFX"
  git -C "$YSFX" checkout -q "$YSFX_COMMIT"
  git -C "$YSFX" submodule update -q --init --recursive
  git -C "$YSFX" apply "$PATCH"
  log "Applied $(basename "$PATCH")"
elif git -C "$YSFX" apply --reverse --check "$PATCH" 2>/dev/null; then
  :  # patch already applied
elif git -C "$YSFX" apply --check "$PATCH" 2>/dev/null; then
  git -C "$YSFX" apply "$PATCH"
  log "Applied $(basename "$PATCH")"
else
  fail "vendor/ysfx doesn't match $(basename "$PATCH"). If you edited ysfx, run scripts/save-ysfx-patch.sh; otherwise delete vendor/ysfx to refetch"
fi

SDKROOT="$(pick_sdk)" || fail "no macOS SDK in $SDK_DIR can link; reinstall the Command Line Tools"
export SDKROOT
log "Using SDK $(basename "$SDKROOT")"

# 2. Configure and build
if $clean; then
  log "Removing $BUILD"
  rm -rf "$BUILD"
fi
# Always configure, so new targets are known before the build starts. After the
# first run (which downloads JUCE) this only regenerates the makefiles.
[ -f "$BUILD/CMakeCache.txt" ] || log "Configuring (first build downloads JUCE; this takes a while)"
configure_log="$(mktemp)"
if ! cmake -S "$YSFX" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_SYSROOT="$SDKROOT" > "$configure_log" 2>&1; then
  grep -E "Error|error" -A3 "$configure_log" | head -30 >&2 || true
  fail "configure failed; full log in $configure_log"
fi
rm -f "$configure_log"
log "Building ${TARGETS[*]} (log: $BUILD/build.log)"
if ! cmake --build "$BUILD" --target "${TARGETS[@]}" -j "$(sysctl -n hw.ncpu)" \
    > "$BUILD/build.log" 2>&1; then
  { grep -E "error:" "$BUILD/build.log" | head -20; tail -5 "$BUILD/build.log"; } >&2 || true
  fail "build failed; full log in $BUILD/build.log"
fi

# 3. Verify
for bundle in "${BUNDLES[@]}"; do
  path="$BUILD/$bundle"
  name="$(basename "$bundle" .vst3)"
  binary="$path/Contents/MacOS/$name"
  [ -f "$binary" ] || fail "$name: binary missing after build"
  for marker in "${MARKERS[@]}"; do
    # grep the binary directly: piping strings into grep -q trips pipefail via SIGPIPE
    grep -qF -- "$marker" "$binary" || fail "$name: missing FL-Agent change ($marker)"
  done
  codesign --verify --deep "$path" || fail "$name: invalid code signature"
  log "Verified $name"
done

# The renderer must compile and run a known-good script
"$BUILD/flagent_render" "$SMOKE_SCRIPT" --input pluck --seconds 1 | grep -q '"compiled": true' \
  || fail "flagent_render smoke test failed on $SMOKE_SCRIPT"
log "Verified flagent_render"

# 4. Install by atomic swap
if $install; then
  mkdir -p "$(dirname "$RENDER_BIN")"
  cp "$BUILD/flagent_render" "$RENDER_BIN.new" && mv "$RENDER_BIN.new" "$RENDER_BIN"
  log "Installed $RENDER_BIN"
  mkdir -p "$DEST"
  for bundle in "${BUNDLES[@]}"; do
    name="$(basename "$bundle")"
    staging="$DEST/.$name.new"
    rm -rf "$staging"
    ditto "$BUILD/$bundle" "$staging"
    if [ -e "$DEST/$name" ]; then
      mv "$DEST/$name" "$DEST/.$name.old"
    fi
    mv "$staging" "$DEST/$name"
    rm -rf "$DEST/.$name.old"
    log "Installed $DEST/$name"
  done
  if pgrep -x OsxFL >/dev/null; then
    log "FL Studio is running: restart it (fl_restart) to load the new plugins"
  fi
fi
log "Done"
