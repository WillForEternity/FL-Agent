# SPDX-License-Identifier: Apache-2.0
"""FL Studio app control: project status, save, open, new, quit, launch, restart.

Built on utils/macos_ui.py (native menu items and process state) plus the
controller script (unsaved-changes flag, readiness checks).

Safety rule: nothing that closes the current project runs while it has
unsaved changes, unless the caller passes discard_unsaved=True. If the
unsaved state can't be determined, that counts as "has unsaved changes".
"""

from __future__ import annotations

import signal
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from fl_studio_mcp.utils import macos_ui
from fl_studio_mcp.utils.macos_ui import UIAutomationError

if TYPE_CHECKING:
    from fastmcp import FastMCP

PROJECTS_DIR = Path.home() / "Documents/Image-Line/FL Studio/Projects"
QUIT_TIMEOUT = 20.0
KILL_TIMEOUT = 10.0
STARTUP_TIMEOUT = 90.0
SAVE_TIMEOUT = 15.0
OPEN_TIMEOUT = 30.0


def unsaved_changes() -> bool | None:
    """True/False from FL's changed flag, or None if FL can't be asked."""
    if not macos_ui.is_running():
        return False
    from fl_studio_mcp.utils.connection import get_connection

    try:
        result = get_connection().send_command("general.getProjectState", timeout=3.0)
    except RuntimeError:
        return None
    if "changed_flag" not in result:
        return None  # FL not responding, or an older controller script
    return result["changed_flag"] != 0


def controller_ready() -> bool:
    """Whether the controller script inside FL answers commands."""
    from fl_studio_mcp.utils.connection import get_connection

    try:
        return get_connection().send_command("transport.getStatus", timeout=2.0).get(
            "success", False
        )
    except RuntimeError:
        return False


def guard_unsaved(discard_unsaved: bool) -> dict | None:
    """Return an error dict if closing the project would lose unsaved work."""
    if discard_unsaved:
        return None
    state = unsaved_changes()
    if state is False:
        return None
    reason = (
        "The current project has unsaved changes"
        if state
        else "Couldn't confirm the current project is saved (FL isn't answering, or "
        "its controller script predates general.getProjectState)"
    )
    return {
        "error": reason,
        "hint": "Save it first with fl_save_project, or pass discard_unsaved=true "
        "if the user agreed to lose the changes",
    }


def project_name() -> str | None:
    """File name of the open project from the window title, e.g. "Project_1.flp"."""
    title = macos_ui.project_window_title()
    return title.split(" - FL Studio")[0] if title else None


def find_project_file(name: str) -> Path | None:
    """Locate a project file by name under FL's Projects folder (newest match)."""
    matches = [p for p in PROJECTS_DIR.rglob(name) if "Backup" not in p.parts]
    return max(matches, key=lambda p: p.stat().st_mtime) if matches else None


def _wait_ready(timeout: float) -> dict | None:
    """Wait for FL to run and its controller to answer. Error dict on timeout."""
    if not macos_ui.wait_for(macos_ui.is_running, timeout=15):
        return {"error": "FL Studio didn't start"}
    if not macos_ui.wait_for(controller_ready, timeout=timeout, interval=1.0):
        try:
            windows = macos_ui.window_names()
        except UIAutomationError:
            windows = []
        # FL's dialogs are custom-drawn windows with no title; their text and
        # buttons aren't visible to Accessibility, so the user has to answer them
        dialog = "" in windows
        return {
            "error": f"FL Studio started but its controller didn't answer within {timeout:.0f}s",
            "windows": windows,
            "hint": "FL is showing a dialog (an untitled window); ask the user what it "
            "says and to answer it" if dialog else "Check that the IAC Driver is online "
            "and the FLStudioMCP controller is enabled",
        }
    return None


def quit_fl(discard_unsaved: bool = False) -> dict:
    """Quit FL Studio, refusing if that would lose unsaved work."""
    if not macos_ui.is_running():
        return {"quit": True, "note": "FL Studio wasn't running"}
    blocked = guard_unsaved(discard_unsaved)
    if blocked:
        return blocked

    macos_ui.request_quit()
    if macos_ui.wait_for(lambda: not macos_ui.is_running(), timeout=QUIT_TIMEOUT):
        return {"quit": True}
    if not discard_unsaved:
        return {"error": "FL Studio didn't quit; a dialog may be waiting for an answer"}

    # The user agreed to discard changes, so get past the save prompt by
    # terminating the process (FL keeps its own autosave backups)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        # pkill takes the signal name without the "SIG" prefix
        subprocess.run(["pkill", f"-{sig.name.removeprefix('SIG')}", "-x", macos_ui.PROCESS_NAME])
        if macos_ui.wait_for(lambda: not macos_ui.is_running(), timeout=KILL_TIMEOUT):
            return {"quit": True, "note": f"Ended with {sig.name}; unsaved changes discarded"}
    return {"error": "FL Studio is still running after SIGKILL"}


def launch_fl(project: str | None = None) -> dict:
    """Start FL Studio, optionally with a project file, and wait until it's ready."""
    if project:
        path = Path(project).expanduser()
        if not path.is_file():
            return {"error": f"Project file not found: {path}"}
        macos_ui.open_with_fl(path)
    else:
        macos_ui.launch()
    error = _wait_ready(STARTUP_TIMEOUT)
    return error or {"running": True, "project": project_name()}


def register_app_tools(mcp: FastMCP) -> None:
    """Register FL Studio app control tools with the MCP server."""

    def _safe(fn, *args, **kwargs) -> dict:
        try:
            return fn(*args, **kwargs)
        except UIAutomationError as e:
            return {"error": str(e)}

    @mcp.tool()
    def fl_project_status() -> dict:
        """Report whether FL Studio is running, the open project, and unsaved changes."""

        def status() -> dict:
            running = macos_ui.is_running()
            if not running:
                return {"running": False}
            name = project_name()
            path = find_project_file(name) if name else None
            return {
                "running": True,
                "project": name,
                "project_path": str(path) if path else None,
                "unsaved_changes": unsaved_changes(),
                "controller_ready": controller_ready(),
            }

        return _safe(status)

    @mcp.tool()
    def fl_save_project() -> dict:
        """Save the open project (File > Save).

        Refuses for a never-saved project, where Save would open a file dialog.
        Confirms the save through FL's unsaved-changes flag.
        """

        def save() -> dict:
            name = project_name()
            if not name or name.lower().startswith("untitled"):
                return {"error": "The project has never been saved; ask the user to save "
                        "it once with a name"}
            macos_ui.click_menu(["File", "Save"])
            if macos_ui.wait_for(lambda: unsaved_changes() is False, timeout=SAVE_TIMEOUT):
                return {"saved": True, "project": name}
            return {"error": "Save didn't complete; a dialog may be open in FL Studio"}

        return _safe(save)

    @mcp.tool()
    def fl_open_project(path: str, discard_unsaved: bool = False) -> dict:
        """Open a project file in FL Studio.

        Args:
            path: Path to a .flp file
            discard_unsaved: Only true if the user agreed to lose unsaved changes
                in the currently open project
        """

        def open_project() -> dict:
            file = Path(path).expanduser()
            if not file.is_file() or file.suffix.lower() != ".flp":
                return {"error": f"Not an .flp file: {file}"}
            if not macos_ui.is_running():
                return launch_fl(str(file))
            blocked = guard_unsaved(discard_unsaved)
            if blocked:
                return blocked
            if discard_unsaved and unsaved_changes() is not False:
                # Opening would show a save prompt; restart instead
                result = quit_fl(discard_unsaved=True)
                return result if "error" in result else launch_fl(str(file))
            macos_ui.open_with_fl(file)
            if not macos_ui.wait_for(lambda: project_name() == file.name, timeout=OPEN_TIMEOUT):
                return {"error": f"FL Studio didn't show {file.name} as the open project"}
            error = _wait_ready(OPEN_TIMEOUT)
            return error or {"opened": str(file)}

        return _safe(open_project)

    @mcp.tool()
    def fl_list_templates() -> dict:
        """List FL Studio's project templates (File > New from template)."""

        def templates() -> dict:
            result = {}
            for category in macos_ui.menu_item_names(["File", "New from template"]):
                if category.endswith(("...", "…")):
                    continue  # menu commands such as "Change default template..."
                try:
                    result[category] = macos_ui.menu_item_names(
                        ["File", "New from template", category]
                    )
                except UIAutomationError:
                    result[category] = []  # a plain menu item, not a category
            return {"templates": result}

        return _safe(templates)

    @mcp.tool()
    def fl_new_project(
        template: list[str] | None = None,
        discard_unsaved: bool = False,
    ) -> dict:
        """Start a new project, optionally from a template.

        Args:
            template: Menu path under File > New from template, as listed by
                fl_list_templates, e.g. ["Minimal", "Empty"]. Omit for File > New.
            discard_unsaved: Only true if the user agreed to lose unsaved changes
        """

        def new_project() -> dict:
            if not macos_ui.is_running():
                error = launch_fl()
                if "error" in error:
                    return error
            blocked = guard_unsaved(discard_unsaved)
            if blocked:
                return blocked
            if discard_unsaved and unsaved_changes() is not False:
                result = quit_fl(discard_unsaved=True)
                if "error" in result:
                    return result
                result = launch_fl()
                if "error" in result:
                    return result
            path = ["File", "New from template", *template] if template else ["File", "New"]
            before = macos_ui.project_window_title()
            macos_ui.click_menu(path)
            changed = macos_ui.wait_for(
                lambda: macos_ui.project_window_title() != before, timeout=OPEN_TIMEOUT
            )
            error = _wait_ready(OPEN_TIMEOUT)
            if error:
                return error
            return {"new_project": True, "template": template, "title_changed": changed}

        return _safe(new_project)

    @mcp.tool()
    def fl_quit(discard_unsaved: bool = False) -> dict:
        """Quit FL Studio.

        Args:
            discard_unsaved: Only true if the user agreed to lose unsaved changes
        """
        return _safe(quit_fl, discard_unsaved)

    @mcp.tool()
    def fl_launch(project: str | None = None) -> dict:
        """Start FL Studio, optionally opening a project, and wait until it's ready.

        Args:
            project: Optional path to a .flp file
        """
        if macos_ui.is_running():
            return {"error": "FL Studio is already running; use fl_open_project"}
        return _safe(launch_fl, project)

    @mcp.tool()
    def fl_restart(reopen_project: bool = True, discard_unsaved: bool = False) -> dict:
        """Quit and relaunch FL Studio, e.g. to load an updated controller script or plugin.

        Args:
            reopen_project: Reopen the current project after the restart
            discard_unsaved: Only true if the user agreed to lose unsaved changes
        """

        def restart() -> dict:
            project = None
            if reopen_project and macos_ui.is_running():
                name = project_name()
                path = find_project_file(name) if name else None
                project = str(path) if path else None
            result = quit_fl(discard_unsaved)
            if "error" in result:
                return result
            launched = launch_fl(project)
            return {**launched, "reopened": project}

        return _safe(restart)

