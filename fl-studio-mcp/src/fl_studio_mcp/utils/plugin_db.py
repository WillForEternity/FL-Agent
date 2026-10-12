# SPDX-License-Identifier: Apache-2.0
"""Load plugins by opening FL Studio plugin-database presets.

FL Studio's scripting API cannot instantiate plugins, but FL Studio loads a
plugin when the OS asks it to open that plugin's preset (.fst) file:
- a generator preset is added to the Channel Rack as a new channel
- an effect preset is added to a free slot on Master (whatever track is selected)

The plugin database in FL's Presets folder holds one .fst per plugin FL knows
about (third-party plugins appear under "Installed" after a plugin scan).

macOS only (uses `open -a`).
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Literal

Kind = Literal["Generators", "Effects"]

USER_DB = Path.home() / "Documents/Image-Line/FL Studio/Presets/Plugin database"


def _db_dirs(kind: Kind) -> list[Path]:
    """Plugin database folders for `kind`, most specific first."""
    return [
        USER_DB / kind,
        USER_DB / "Installed" / kind,
        *Path("/Applications").glob(
            f"FL Studio*.app/Contents/Resources/FL/Data/Patches/Plugin database/{kind}"
        ),
    ]


def find_plugins(kind: Kind) -> dict[str, tuple[str, Path]]:
    """Map lowercase plugin name -> (category, .fst path)."""
    found: dict[str, tuple[str, Path]] = {}
    for root in _db_dirs(kind):
        if not root.is_dir():
            continue
        for fst in sorted(root.rglob("*.fst")):
            key = fst.stem.lower()
            if key not in found:
                found[key] = (fst.parent.relative_to(root).as_posix(), fst)
    return found


def list_plugins(kind: Kind, query: str = "") -> list[dict]:
    """List plugins of `kind`, filtered by a case-insensitive name/category query."""
    q = query.lower()
    return [
        {"name": path.stem, "category": category}
        for category, path in find_plugins(kind).values()
        if not q or q in path.stem.lower() or q in category.lower()
    ]


def resolve_plugin(kind: Kind, name: str) -> tuple[Path | None, list[str]]:
    """Return (preset path, suggestions). Path is None when there's no exact match."""
    plugins = find_plugins(kind)
    match = plugins.get(name.lower())
    if match is not None:
        return match[1], []
    close = [path.stem for _, path in plugins.values() if name.lower() in path.stem.lower()]
    return None, close[:10]


def open_in_fl(preset: Path) -> str | None:
    """Ask FL Studio to open a preset file. Returns an error message on failure."""
    if platform.system() != "Darwin":
        return "Loading plugins currently supports macOS only"
    apps = sorted(Path("/Applications").glob("FL Studio*.app"))
    if not apps:
        return "FL Studio app not found in /Applications"
    subprocess.run(["open", "-a", str(apps[-1]), str(preset)], check=True, timeout=10)
    return None
