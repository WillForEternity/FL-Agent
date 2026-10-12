#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Regenerate patches/ysfx-flagent.patch from the working tree in vendor/ysfx.
# Run after editing ysfx; commit the patch, not vendor/ysfx (which is gitignored).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
YSFX="$ROOT/vendor/ysfx"
PATCH="$ROOT/patches/ysfx-flagent.patch"

[ -d "$YSFX/.git" ] || { echo "ERROR: no ysfx checkout at $YSFX" >&2; exit 1; }

# Include new files: mark untracked files as intent-to-add for the diff, then undo
untracked="$(git -C "$YSFX" ls-files --others --exclude-standard -- plugin tools sources include cmake '*.txt')"
if [ -n "$untracked" ]; then
  echo "$untracked" | (cd "$YSFX" && xargs -I{} git add -N "{}")
fi
git -C "$YSFX" diff --binary > "$PATCH.new"
if [ -n "$untracked" ]; then
  echo "$untracked" | (cd "$YSFX" && xargs -I{} git reset -q "{}")
fi
mv "$PATCH.new" "$PATCH"
echo "Wrote $PATCH ($(grep -c '^diff --git' "$PATCH") files)"
