# SPDX-License-Identifier: Apache-2.0
"""Instrument loading tools for FL Studio.

Instruments are loaded by opening their plugin-database preset in FL Studio,
which adds them to the Channel Rack (see utils/plugin_db.py). macOS only.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fl_studio_mcp.utils.plugin_db import list_plugins, open_in_fl, resolve_plugin

if TYPE_CHECKING:
    from fastmcp import FastMCP

# How long to wait for FL Studio to add the new channel
LOAD_TIMEOUT = 8.0
POLL_INTERVAL = 0.25


def load_instrument(
    name: str,
    mixer_track: int | None = None,
    channel_name: str | None = None,
) -> dict:
    """Load a generator into a new channel, then optionally route and rename it."""
    from fl_studio_mcp.utils.connection import get_connection

    fst, suggestions = resolve_plugin("Generators", name)
    if fst is None:
        return {"error": f"Instrument '{name}' not found", "did_you_mean": suggestions}

    conn = get_connection()
    before = conn.send_command("channels.getCount", {"global_count": True})
    if "count" not in before:
        return {"error": before.get("error", "Could not read channel count")}
    count_before = before["count"]

    error = open_in_fl(fst)
    if error:
        return {"error": error}

    deadline = time.monotonic() + LOAD_TIMEOUT
    index = None
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL)
        now = conn.send_command("channels.getCount", {"global_count": True})
        if now.get("count", count_before) > count_before:
            index = now["count"] - 1
            break
    if index is None:
        return {
            "error": f"FL Studio did not add a channel for '{fst.stem}' "
            f"within {LOAD_TIMEOUT}s"
        }

    result = {"loaded": fst.stem, "channel_index": index}
    if mixer_track is not None:
        routed = conn.send_command("channels.routeToMixer", {
            "channel_index": index,
            "mixer_track": mixer_track,
        })
        ok = routed.get("success", False)
        result["mixer_track"] = mixer_track if ok else routed.get("error")
    if channel_name:
        renamed = conn.send_command("channels.setName", {"index": index, "name": channel_name})
        ok = renamed.get("success", False)
        result["channel_name"] = channel_name if ok else renamed.get("error")
    return result


def register_instrument_tools(mcp: FastMCP) -> None:
    """Register instrument loading tools with the MCP server."""

    @mcp.tool()
    def fl_list_instruments(query: str = "") -> dict:
        """List instruments (generator plugins) that fl_load_instrument can load.

        Covers FL Studio's built-in generators plus third-party instruments
        that FL Studio's plugin scan has added to the plugin database.

        Args:
            query: Optional case-insensitive filter on name or category
        """
        instruments = list_plugins("Generators", query)
        return {"count": len(instruments), "instruments": instruments}

    @mcp.tool()
    def fl_load_instrument(
        name: str,
        mixer_track: int | None = None,
        channel_name: str | None = None,
    ) -> dict:
        """Load an instrument into a new Channel Rack channel.

        Opens the instrument's plugin-database preset in FL Studio, waits for
        the new channel to appear, then optionally routes and renames it.
        Plugins not included in the user's FL Studio edition load in demo mode.

        Args:
            name: Instrument name as shown by fl_list_instruments (e.g. "FL Keys")
            mixer_track: Optional mixer track to route the new channel to
            channel_name: Optional name for the new channel
        """
        return load_instrument(name, mixer_track, channel_name)
