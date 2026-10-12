# SPDX-License-Identifier: Apache-2.0
"""Custom DSP tools: write JSFX effects and instruments and run them in FL Studio.

Scripts run inside the "FL-Agent FX" / "FL-Agent instrument" plugins, a
modified build of ysfx (vendor/ysfx). Three modifications make them scriptable:
- A new plugin instance loads the script named in PENDING_FILE (if written in
  the last 30 seconds), so a tool can choose what a fresh instance runs. Used
  for instruments, which FL adds as new channels.
- The "FL-Agent assign" parameter points one existing instance at a script.
  Used for effects: FL puts effect presets opened from outside on Master, so
  the user adds a blank FL-Agent FX to a track and Claude assigns it a script.
- The plugin reloads its script, keeping slider values, when the file changes,
  so fl_update_dsp edits sound immediately.

Each JSFX `sliderN:` becomes a host parameter, tunable with
fl_get_plugin_params / fl_set_plugin_param_value.
"""

from __future__ import annotations

import os
import random
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING

from fl_studio_mcp.tools.effects import get_slots
from fl_studio_mcp.tools.instruments import load_instrument

if TYPE_CHECKING:
    from fastmcp import FastMCP

# Scripts live in the FL-Agent project folder unless overridden
DSP_DIR = Path(
    os.environ.get("FL_AGENT_DSP_DIR", Path(__file__).resolve().parents[3].parent / "dsp")
)
PENDING_FILE = Path.home() / "Library/Application Support/FL-Agent/ysfx/pending.txt"
FX_PLUGIN = "FL-Agent FX"
INSTRUMENT_PLUGIN = "FL-Agent instrument"
ASSIGN_PARAM = "FL-Agent assign"
# The plugin decodes the assign parameter as round(value * TOKEN_SCALE)
# (must match kAgentTokenScale in processor.cpp). FL Studio rounds this
# parameter to 2 decimal places on the way to the plugin (0.328125 arrives
# as 0.33), so only send values of the form k / 100.
TOKEN_SCALE = 1_000_000
TOKEN_STEPS = 100
ASSIGN_TIMEOUT = 6.0


def _script_path(name: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"Invalid DSP name: {name!r}")
    return DSP_DIR / f"{slug}.jsfx"


def _write_script(name: str, code: str) -> Path:
    """Write a JSFX script, adding a desc: line if the code has none."""
    if not re.search(r"^\s*desc:", code, re.MULTILINE):
        code = f"desc:{name}\n{code}"
    path = _script_path(name)
    DSP_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(code)
    return path


def _queue_script(path: Path) -> None:
    """Tell the next FL-Agent plugin instance to load `path`."""
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    PENDING_FILE.write_text(str(path))


def new_assign_token(rng: random.Random | None = None) -> tuple[float, int]:
    """Pick an assign parameter value and the request-file token the plugin derives from it."""
    value = (rng or random).randint(1, TOKEN_STEPS - 1) / TOKEN_STEPS
    return value, round(value * TOKEN_SCALE)


def _assign_script(path: Path, mixer_track: int, slot_index: int | None) -> dict:
    """Point an FL-Agent FX already on `mixer_track` at the script at `path`."""
    from fl_studio_mcp.utils.connection import get_connection

    slots = get_slots(mixer_track)
    if "error" in slots:
        return slots
    agent_slots = [i for i, n in slots.items() if n == FX_PLUGIN]
    if slot_index is None:
        if not agent_slots:
            return {
                "error": f"No {FX_PLUGIN} on mixer track {mixer_track}",
                "hint": f"Ask the user to add a blank {FX_PLUGIN} to an empty slot "
                f"of mixer track {mixer_track}, then retry",
            }
        slot_index = agent_slots[0]
    elif slot_index not in agent_slots:
        return {"error": f"Slot {slot_index} of track {mixer_track} is not {FX_PLUGIN}"}

    conn = get_connection()
    target = {"index": mixer_track, "slot_index": slot_index}
    found = conn.send_command("plugins.findParam", {**target, "name": ASSIGN_PARAM})
    param = found.get("param_index", -1)
    if param < 0:
        return {"error": f"'{ASSIGN_PARAM}' parameter not found; is the plugin up to date?"}

    value, token = new_assign_token()
    request = PENDING_FILE.with_name(f"assign-{token}.txt")
    request.parent.mkdir(parents=True, exist_ok=True)
    request.write_text(str(path))
    conn.send_command("plugins.setParamValue", {
        "param_index": param,
        "value": value,
        "plugin_index": mixer_track,
        "slot_index": slot_index,
    })

    # The plugin deletes the request file once it has loaded the script
    deadline = time.monotonic() + ASSIGN_TIMEOUT
    while request.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    if request.exists():
        request.unlink(missing_ok=True)
        return {"error": "The plugin didn't pick up the script (is it the rebuilt version?)"}
    return {"mixer_track": mixer_track, "slot_index": slot_index, "script": str(path)}


def _load_instrument_script(path: Path, channel_name: str, mixer_track: int | None) -> dict:
    """Load the script at `path` into a new FL-Agent instrument channel."""
    _queue_script(path)
    result = load_instrument(INSTRUMENT_PLUGIN, mixer_track, channel_name=channel_name)
    if "error" in result:
        PENDING_FILE.unlink(missing_ok=True)
        return _not_installed(result)
    return {**result, "script": str(path)}


def _not_installed(result: dict) -> dict:
    if "not found" in result.get("error", ""):
        result["hint"] = (
            "The FL-Agent plugins aren't in FL Studio's plugin database yet. "
            "Build/install them (vendor/ysfx) and run Options > Manage plugins > Find plugins."
        )
    return result


def register_dsp_tools(mcp: FastMCP) -> None:
    """Register custom DSP tools with the MCP server."""

    @mcp.tool()
    def fl_create_dsp_effect(
        name: str,
        code: str,
        mixer_track: int,
        slot_index: int | None = None,
    ) -> dict:
        """Write a JSFX effect and run it in an FL-Agent FX on a mixer track.

        The track must already have an FL-Agent FX in one of its slots (the user
        adds a blank one once per track); this assigns the script to it,
        replacing whatever it was running. FL can't place new effects on a
        chosen track from outside, so this never loads new plugins.

        `code` is a complete JSFX script (desc:, sliderN: lines, @init, @slider,
        @sample, ...). Process audio in @sample via spl0/spl1. Sliders become
        host parameters tunable with fl_set_plugin_param_value
        (plugin_index=mixer_track, slot_index from the result).

        Args:
            name: Effect name; also used for the script file name
            code: JSFX source code
            mixer_track: Mixer track holding the FL-Agent FX (0 = Master)
            slot_index: Which FL-Agent FX slot to use (default: the first one)
        """
        return _assign_script(_write_script(name, code), mixer_track, slot_index)

    @mcp.tool()
    def fl_assign_dsp_effect(
        name: str,
        mixer_track: int,
        slot_index: int | None = None,
    ) -> dict:
        """Run an existing custom effect script in an FL-Agent FX on a mixer track.

        Like fl_create_dsp_effect but reuses a script already written, e.g. to
        put the same effect on several tracks.

        Args:
            name: Name used when the effect was created
            mixer_track: Mixer track holding the FL-Agent FX (0 = Master)
            slot_index: Which FL-Agent FX slot to use (default: the first one)
        """
        path = _script_path(name)
        if not path.exists():
            return {"error": f"No DSP script named '{name}'"}
        return _assign_script(path, mixer_track, slot_index)

    @mcp.tool()
    def fl_create_dsp_instrument(
        name: str,
        code: str,
        mixer_track: int | None = None,
    ) -> dict:
        """Write a JSFX instrument and load it into a new Channel Rack channel.

        `code` is a complete JSFX script that reads MIDI with midirecv() in
        @block or @sample and writes audio to spl0/spl1. The channel is named
        after the instrument; select it to play it from a MIDI keyboard.

        Args:
            name: Instrument name; also used for the channel and script file name
            code: JSFX source code
            mixer_track: Optional mixer track to route the new channel to
        """
        return _load_instrument_script(_write_script(name, code), name, mixer_track)

    @mcp.tool()
    def fl_load_dsp_instrument(name: str, mixer_track: int | None = None) -> dict:
        """Load an existing custom instrument script into a new Channel Rack channel.

        Like fl_create_dsp_instrument, but reuses a script already in the DSP
        folder (e.g. one checked offline with bin/flagent_render).

        Args:
            name: Script name (as listed by fl_list_dsp, or its display name)
            mixer_track: Optional mixer track to route the new channel to
        """
        path = _script_path(name)
        if not path.exists():
            return {"error": f"No DSP script named '{name}'"}
        return _load_instrument_script(path, name, mixer_track)

    @mcp.tool()
    def fl_update_dsp(name: str, code: str) -> dict:
        """Replace the code of an existing custom effect or instrument.

        Every plugin instance running this script reloads it within about half
        a second, keeping current slider values.

        Args:
            name: Name used when the effect/instrument was created
            code: New JSFX source code
        """
        if not _script_path(name).exists():
            return {"error": f"No DSP script named '{name}'"}
        return {"updated": str(_write_script(name, code))}

    @mcp.tool()
    def fl_read_dsp(name: str) -> dict:
        """Read the JSFX source of a custom effect or instrument.

        Args:
            name: Name used when the effect/instrument was created
        """
        path = _script_path(name)
        if not path.exists():
            return {"error": f"No DSP script named '{name}'"}
        return {"script": str(path), "code": path.read_text()}

    @mcp.tool()
    def fl_list_dsp() -> dict:
        """List the custom JSFX effects and instruments written so far."""
        scripts = sorted(DSP_DIR.glob("*.jsfx")) if DSP_DIR.is_dir() else []
        return {"dsp_dir": str(DSP_DIR), "scripts": [p.stem for p in scripts]}
