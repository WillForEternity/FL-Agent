# SPDX-License-Identifier: Apache-2.0
"""macOS automation of the FL Studio app: launching, quitting and menu commands.

FL Studio's windows are custom-drawn, so their contents aren't visible to
macOS Accessibility, but its menu bar is native. Everything here therefore
works through menu items addressed by name (never screen coordinates) and
through the app's process state, which keeps it independent of window layout.

Requires Accessibility permission for the app running the MCP server
(System Settings > Privacy & Security > Accessibility). macOS only.
"""

from __future__ import annotations

import platform
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path

PROCESS_NAME = "OsxFL"
OSASCRIPT_TIMEOUT = 30.0


class UIAutomationError(RuntimeError):
    """An automation step failed; the message says which and why."""


def applescript_string(text: str) -> str:
    """Quote `text` as an AppleScript string literal."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def run_applescript(script: str, timeout: float = OSASCRIPT_TIMEOUT) -> str:
    """Run an AppleScript and return its output, raising UIAutomationError on failure."""
    if platform.system() != "Darwin":
        raise UIAutomationError("App automation is macOS only")
    try:
        result = subprocess.run(
            ["osascript", "-"], input=script, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as e:
        raise UIAutomationError(f"AppleScript timed out after {timeout:.0f}s") from e
    if result.returncode != 0:
        message = result.stderr.strip()
        if "not allowed assistive access" in message or "-1719" in message:
            message += (
                " (grant Accessibility permission to the app running Claude Code in "
                "System Settings > Privacy & Security > Accessibility)"
            )
        raise UIAutomationError(message)
    return result.stdout.strip()


def find_app() -> Path:
    """Return the newest FL Studio app bundle in /Applications."""
    apps = sorted(Path("/Applications").glob("FL Studio*.app"))
    if not apps:
        raise UIAutomationError("FL Studio app not found in /Applications")
    return apps[-1]


def is_running() -> bool:
    """Whether the FL Studio process is running."""
    result = subprocess.run(["pgrep", "-x", PROCESS_NAME], capture_output=True)
    return result.returncode == 0


def wait_for(condition: Callable[[], bool], timeout: float, interval: float = 0.25) -> bool:
    """Poll `condition` until it's true or `timeout` seconds pass. Returns the final result."""
    deadline = time.monotonic() + timeout
    while True:
        if condition():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)


def window_names() -> list[str]:
    """Names of FL Studio's open windows (front first)."""
    out = run_applescript(
        f'tell application "System Events" to tell process "{PROCESS_NAME}" '
        "to get name of every window"
    )
    return [name.strip() for name in out.split(",")] if out else []


def menu_item_names(path: Sequence[str]) -> list[str]:
    """Names of the items in the menu at `path` (e.g. ["File", "New from template"])."""
    if not path:
        raise ValueError("path must name at least a menu bar item")
    ref = f"menu bar item {applescript_string(path[0])} of menu bar 1"
    for name in path[1:]:
        ref = f"menu item {applescript_string(name)} of menu 1 of {ref}"
    out = run_applescript(
        f'tell application "System Events" to tell process "{PROCESS_NAME}" '
        f"to get name of every menu item of menu 1 of {ref}"
    )
    return [n.strip() for n in out.split(",") if n.strip() and n.strip() != "missing value"]


def click_menu(path: Sequence[str]) -> None:
    """Click the FL Studio menu item at `path`, e.g. ["File", "Save"]."""
    if len(path) < 2:
        raise ValueError("path must name a menu bar item and at least one menu item")
    ref = f"menu bar item {applescript_string(path[0])} of menu bar 1"
    for name in path[1:-1]:
        ref = f"menu item {applescript_string(name)} of menu 1 of {ref}"
    ref = f"menu item {applescript_string(path[-1])} of menu 1 of {ref}"
    run_applescript(
        f'tell application "{find_app().stem}" to activate\n'
        "delay 0.3\n"
        f'tell application "System Events" to tell process "{PROCESS_NAME}" to click {ref}'
    )


def project_window_title() -> str | None:
    """Title of the main project window, e.g. "Project_1.flp - FL Studio 2026"."""
    for name in window_names():
        if " - FL Studio" in name:
            return name
    return None


def open_with_fl(path: Path) -> None:
    """Ask macOS to open `path` in FL Studio (starts FL if needed)."""
    subprocess.run(["open", "-a", str(find_app()), str(path)], check=True, timeout=15)


def launch() -> None:
    """Start FL Studio (no file)."""
    subprocess.run(["open", "-a", str(find_app())], check=True, timeout=15)


def request_quit() -> None:
    """Ask FL Studio to quit, as if the user chose Exit.

    Callers must check is_running() afterwards: FL answers the quit Apple
    Event with error -128 ("User canceled") even when it does quit, so the
    reply can't tell success from a cancelled save prompt.
    """
    try:
        run_applescript(f'tell application "{find_app().stem}" to quit', timeout=10)
    except UIAutomationError as e:
        if "-128" not in str(e):
            raise
