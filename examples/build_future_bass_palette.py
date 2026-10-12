# SPDX-License-Identifier: Apache-2.0
"""Example: build a 12-track future-bass sound palette in the open FL project.

Open a fresh project made from the FL-Agent template (docs/getting-started.md),
then run:

    cd fl-studio-mcp && uv run python ../examples/build_future_bass_palette.py

The script refuses to run on a project that already has channels beyond the
template's, so it can't add duplicate tracks.

Every track gets its own channel and mixer insert, a name, a colour and a
starting volume; custom effects go into the FL-Agent FX in slot 10 of each
insert. A halftime beat is programmed into Pattern 1. Each step is checked and
a summary is printed as JSON.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass

from fl_studio_mcp.tools.dsp import _assign_script, _load_instrument_script, _script_path
from fl_studio_mcp.tools.instruments import load_instrument
from fl_studio_mcp.utils.connection import get_connection

TEMPO = 150
FX_SLOT = 9  # slot 10 in FL's numbering


@dataclass
class Track:
    insert: int
    name: str
    source: str           # "dsp:<script>" or an FL plugin name
    color: tuple[int, int, int]
    volume: float         # channel volume, 0-1
    effect: str | None = None
    effect_params: dict[int, float] | None = None  # normalised plugin values


# Palette: drums warm/earthy, harmony greens, leads pinks, textures blues
TRACKS = [
    Track(1, "Kick", "dsp:Bloom Kick", (200, 120, 60), 0.80),
    Track(2, "Clap", "dsp:Snap Clap", (210, 150, 80), 0.70),
    Track(3, "Hats", "dsp:Silk Hats", (220, 180, 110), 0.60),
    Track(4, "FPC Kit", "FPC", (180, 110, 70), 0.70),
    # Supersaw chords pump on every beat
    Track(5, "Supersaw", "dsp:Bloom Saw", (120, 200, 120), 0.70, "Petal Pump"),
    # Sub pumps less, so the low end keeps its weight
    Track(6, "Sub", "dsp:Root Sub", (80, 160, 90), 0.75, "Petal Pump", {0: 0.5}),
    # Vocal chops: dotted-1/8 delay at 150 BPM = 300 ms -> (300 - 10) / 1990
    Track(7, "Fairy Vox", "dsp:Fairy Vox", (230, 140, 190), 0.70, "Petal Delay",
          {0: (300 - 10) / 1990}),
    Track(8, "Glass Bells", "dsp:Glass Bloom", (240, 170, 210), 0.65, "Moss Verb"),
    Track(9, "Keys", "FL Keys", (150, 210, 160), 0.70, "Moss Verb", {3: 0.22}),
    Track(10, "Plucks", "Plucked!", (190, 230, 170), 0.65, "Petal Delay",
          {0: (300 - 10) / 1990, 5: 0.25}),
    Track(11, "Pad", "FLEX", (120, 170, 230), 0.60, "Petal Pump", {0: 0.45}),
    Track(12, "Riser", "dsp:Wind Riser", (150, 190, 240), 0.50, "Moss Verb"),
]

# Halftime future-bass beat, 16 steps = 1 bar
BEAT = {
    "Kick": [0, 10],
    "Clap": [8],
    "Hats": [2, 6, 10, 14],
}


def fail(message: str, detail: object) -> None:
    print(json.dumps({"error": message, "detail": detail}, indent=2))
    sys.exit(1)


def main() -> None:
    conn = get_connection()
    summary: dict[str, object] = {}

    existing = conn.send_command("channels.getAll").get("channels")
    if existing is None:
        fail("FL Studio isn't answering", existing)
    if len(existing) > 1:
        fail("this project already has channels; start from a fresh FL-Agent template project",
             [ch["name"] for ch in existing])

    result = conn.send_command("transport.setTempo", {"bpm": TEMPO})
    if abs(result.get("tempo", 0) - TEMPO) > 0.01:
        fail("tempo not set", result)
    summary["tempo"] = result["tempo"]

    channels: dict[str, int] = {}
    for track in TRACKS:
        if track.source.startswith("dsp:"):
            script = track.source[4:]
            loaded = _load_instrument_script(_script_path(script), track.name, track.insert)
        else:
            loaded = load_instrument(track.source, track.insert, track.name)
        if "error" in loaded or loaded.get("mixer_track") != track.insert:
            fail(f"loading {track.name}", loaded)
        index = loaded["channel_index"]
        channels[track.name] = index

        r, g, b = track.color
        conn.send_command("channels.setColor", {"index": index, "r": r, "g": g, "b": b})
        conn.send_command("channels.setVolume", {"index": index, "volume": track.volume})
        conn.send_command("mixer.setTrackName", {"track": track.insert, "name": track.name})
        conn.send_command("mixer.setTrackColor", {"track": track.insert, "r": r, "g": g, "b": b})

        entry: dict[str, object] = {"channel": index, "insert": track.insert}
        if track.effect:
            assigned = _assign_script(_script_path(track.effect), track.insert, FX_SLOT)
            if "error" in assigned:
                fail(f"effect on {track.name}", assigned)
            for param, value in (track.effect_params or {}).items():
                conn.send_command("plugins.setParamValue", {
                    "param_index": param, "value": value,
                    "plugin_index": track.insert, "slot_index": FX_SLOT,
                })
            entry["effect"] = track.effect
        summary[track.name] = entry

    for name, steps in BEAT.items():
        pattern = [i in steps for i in range(16)]
        result = conn.send_command("channels.setStepSequence", {
            "channel": channels[name], "pattern": pattern,
        })
        if not result.get("success", False):
            fail(f"beat for {name}", result)
    summary["beat"] = BEAT

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
