# SPDX-License-Identifier: Apache-2.0
"""Mixer effect loading tools for FL Studio.

Effects are loaded by opening the effect's plugin-database preset (see
utils/plugin_db.py). FL Studio puts effects opened this way on **Master**,
whatever track is selected or focused, so the result reports where the effect
actually landed. To put custom effects on a specific track, use the DSP tools,
which assign scripts to an FL-Agent FX already on that track. macOS only.

Once loaded, an effect's parameters are tuned with the plugin tools
(fl_get_plugin_params / fl_set_plugin_param_value with slot_index).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fl_studio_mcp.utils.plugin_db import list_plugins, open_in_fl, resolve_plugin

if TYPE_CHECKING:
    from fastmcp import FastMCP

# How long to wait for FL Studio to fill the new slot
LOAD_TIMEOUT = 8.0
POLL_INTERVAL = 0.25


def get_slots(track: int) -> dict:
    """Return {slot index: plugin name} for a mixer track, or {"error": ...}."""
    from fl_studio_mcp.utils.connection import get_connection

    result = get_connection().send_command("mixer.getSlots", {"track": track})
    if "slots" not in result:
        return {"error": result.get("error", "Could not read mixer slots")}
    return {s["slot"]: s["name"] for s in result["slots"]}


def load_effect(name: str, mixer_track: int) -> dict:
    """Load an effect into the next free slot of `mixer_track`."""
    from fl_studio_mcp.utils.connection import get_connection

    fst, suggestions = resolve_plugin("Effects", name)
    if fst is None:
        return {"error": f"Effect '{name}' not found", "did_you_mean": suggestions}

    before = get_slots(mixer_track)
    if "error" in before:
        return before
    master_before = get_slots(0)

    conn = get_connection()
    selected = conn.send_command("mixer.setActiveTrack", {"track": mixer_track})
    if not selected.get("success", False):
        return {"error": selected.get("error", "Could not select mixer track")}

    # FL loads an opened preset into the focused window. If a plugin window
    # has focus, the preset could replace that plugin, so refuse to continue.
    focus = {k: v for k, v in selected.items() if k.startswith(("focused", "mixer_", "current"))}
    if selected.get("current") != mixer_track or not selected.get("mixer_focused", False):
        return {
            "error": "Could not focus the Mixer on the target track; not loading, "
            "to avoid replacing a plugin in a focused window",
            "focus": focus,
        }

    error = open_in_fl(fst)
    if error:
        return {"error": error}

    deadline = time.monotonic() + LOAD_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL)
        now = get_slots(mixer_track)
        added = [slot for slot in now if slot != "error" and slot not in before]
        if added:
            return {"loaded": fst.stem, "mixer_track": mixer_track, "slot_index": added[0]}
        # FL Studio currently puts opened effect presets on Master regardless of
        # the selected/focused track (see docs/custom-dsp.md)
        master_added = [s for s in get_slots(0) if s != "error" and s not in master_before]
        if mixer_track != 0 and master_added:
            return {
                "loaded": fst.stem,
                "mixer_track": 0,
                "slot_index": master_added[0],
                "warning": f"FL Studio put the effect on Master, not track {mixer_track}",
            }
    return {
        "error": f"FL Studio did not add '{fst.stem}' to mixer track {mixer_track} "
        f"within {LOAD_TIMEOUT}s (all 10 slots may be full)",
        "focus_before_load": focus,
        "focus_after_load": conn.send_command("ui.getFocus"),
    }


def register_effect_tools(mcp: FastMCP) -> None:
    """Register mixer effect tools with the MCP server."""

    @mcp.tool()
    def fl_list_effects(query: str = "") -> dict:
        """List effect plugins that fl_load_effect can load.

        Covers FL Studio's built-in effects plus third-party effects that
        FL Studio's plugin scan has added to the plugin database.

        Args:
            query: Optional case-insensitive filter on name or category
        """
        effects = list_plugins("Effects", query)
        return {"count": len(effects), "effects": effects}

    @mcp.tool()
    def fl_get_mixer_slots(track: int) -> dict:
        """List the effects loaded in a mixer track's 10 slots.

        Args:
            track: Mixer track index (0 = Master)
        """
        slots = get_slots(track)
        if "error" in slots:
            return slots
        return {"track": track, "slots": [{"slot": i, "name": n} for i, n in slots.items()]}

    @mcp.tool()
    def fl_load_effect(name: str, mixer_track: int) -> dict:
        """Load an effect into a mixer slot.

        Caution: FL Studio puts effects opened from outside on Master, whatever
        track is requested; the result says where it actually landed. Prefer
        asking the user to add effects to other tracks by hand.

        Tune it afterwards with fl_get_plugin_params / fl_set_plugin_param_value,
        passing plugin_index=mixer_track and slot_index from the result.
        Plugins not included in the user's FL Studio edition load in demo mode.

        Args:
            name: Effect name as shown by fl_list_effects (e.g. "Fruity Reeverb 2")
            mixer_track: Mixer track to add it to (0 = Master)
        """
        return load_effect(name, mixer_track)
