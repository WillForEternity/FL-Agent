# SPDX-License-Identifier: Apache-2.0
"""Hot reload of the tool modules.

Claude Code starts the MCP server once per session, so edits to tool code
would otherwise need a new session. reload_tools() re-imports the tool
modules in place and re-registers their tools on the running server.

Not reloaded:
- server.py (the server object and the core tools defined there)
- utils.connection / utils.midi_connection, which hold the open MIDI port;
  changes to those still need a new session.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

# Dependency order: modules are reloaded after everything they import
RELOAD_ORDER = (
    "fl_studio_mcp.utils.plugin_db",
    "fl_studio_mcp.utils.fl_trigger",
    "fl_studio_mcp.utils.macos_ui",
    "fl_studio_mcp.tools.transport",
    "fl_studio_mcp.tools.mixer",
    "fl_studio_mcp.tools.channels",
    "fl_studio_mcp.tools.plugins",
    "fl_studio_mcp.tools.piano_roll",
    "fl_studio_mcp.tools.instruments",
    "fl_studio_mcp.tools.effects",
    "fl_studio_mcp.tools.dsp",
    "fl_studio_mcp.tools.app",
    "fl_studio_mcp.tools",
)

# Tools defined in server.py; they survive a reload untouched
CORE_TOOLS = frozenset({"fl_connect", "fl_connection_status", "fl_reload_tools"})


def _source_path(module_name: str) -> Path | None:
    module = sys.modules.get(module_name)
    spec = importlib.util.find_spec(module_name) if module is None else module.__spec__
    return Path(spec.origin) if spec and spec.origin else None


def check_sources(module_names: tuple[str, ...] = RELOAD_ORDER) -> list[str]:
    """Compile every module's source without running it. Returns error messages."""
    errors = []
    for name in module_names:
        path = _source_path(name)
        if path is None:
            errors.append(f"{name}: source file not found")
            continue
        try:
            compile(path.read_text(), str(path), "exec")
        except SyntaxError as e:
            errors.append(f"{name}: {e.msg} ({path.name}, line {e.lineno})")
    return errors


async def _tool_names(mcp: FastMCP) -> set[str]:
    return {tool.name for tool in await mcp.list_tools()}


async def reload_tools(mcp: FastMCP) -> dict:
    """Reload the tool modules and re-register their tools on `mcp`.

    Nothing is changed if any module fails to compile, so a typo can't take
    the working tools down.
    """
    errors = check_sources()
    if errors:
        return {"reloaded": False, "errors": errors}

    before = await _tool_names(mcp) - CORE_TOOLS

    try:
        for name in RELOAD_ORDER:
            if name in sys.modules:
                importlib.reload(sys.modules[name])
            else:
                importlib.import_module(name)
    except Exception as e:  # noqa: BLE001 - reported to the caller
        return {
            "reloaded": False,
            "errors": [f"{type(e).__name__} while importing: {e}"],
            "note": "Some modules may be half-reloaded; the old tools are still "
            "registered. Fix the error and reload again, or start a new session.",
        }

    for name in before:
        mcp.local_provider.remove_tool(name)
    sys.modules["fl_studio_mcp.tools"].register_all_tools(mcp)

    after = await _tool_names(mcp) - CORE_TOOLS
    return {
        "reloaded": True,
        "tool_count": len(after),
        "added": sorted(after - before),
        "removed": sorted(before - after),
    }
