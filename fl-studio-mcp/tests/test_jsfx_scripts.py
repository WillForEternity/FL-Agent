# SPDX-License-Identifier: Apache-2.0
"""Checks every JSFX script in the DSP folder (no FL Studio needed).

1. Lint: EEL2 identifiers are case-insensitive, so `U` and `u` are the same
   variable. Mixing cases silently aliases variables (this once made Bloom Saw
   render silence), so any identifier used with two different spellings fails.
2. Render: each script is run through bin/flagent_render (built by
   scripts/build-plugins.sh). Instruments get a chord, effects a plucked input.
   The output must compile, contain no NaN/inf, not clip, not be silent, and
   decay after the input/notes stop (no runaway feedback).
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

from fl_studio_mcp.tools.dsp import DSP_DIR

RENDERER = DSP_DIR.parent / "bin" / "flagent_render"
SCRIPTS = sorted(DSP_DIR.glob("*.jsfx"))

# Words that aren't variables: section names, slider declarations, built-ins
IGNORED = {"desc", "slider", "in_pin", "out_pin", "import", "options", "filename"}
IDENTIFIER = re.compile(r"(?<![\w.$#])([A-Za-z_][A-Za-z0-9_]*)")


def code_only(source: str) -> str:
    """The script with comments, strings and slider/desc lines removed."""
    lines = []
    for line in source.splitlines():
        if re.match(r"\s*(desc|slider\d+|in_pin|out_pin|options|import|filename):", line):
            continue
        lines.append(line.split("//")[0])
    text = "\n".join(lines)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r'"[^"]*"', "", text)


def is_instrument(source: str) -> bool:
    return "midirecv" in source


def render(script: Path, *args: str) -> dict:
    out = subprocess.run(
        [str(RENDERER), str(script), *args], capture_output=True, text=True, timeout=60
    )
    return json.loads(out.stdout)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.stem)
def test_no_identifiers_differing_only_in_case(script):
    spellings: dict[str, set[str]] = {}
    for name in IDENTIFIER.findall(code_only(script.read_text())):
        if name.lower() not in IGNORED:
            spellings.setdefault(name.lower(), set()).add(name)
    clashes = {k: v for k, v in spellings.items() if len(v) > 1}
    assert not clashes, f"case-insensitive name clashes: {clashes}"


@pytest.mark.skipif(not RENDERER.exists(), reason="run scripts/build-plugins.sh first")
@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.stem)
def test_script_renders_cleanly(script):
    source = script.read_text()
    if is_instrument(source):
        result = render(script, "--notes", "48,60,64,67,71", "--hold", "1.5", "--seconds", "6")
    else:
        result = render(script, "--input", "pluck", "--input-seconds", "0.3", "--seconds", "8")
    assert result["compiled"], result.get("log")
    assert result["non_finite_samples"] == 0
    assert not result["clipping"], f"peak {result['peak_db']} dBFS"
    assert not result["silent"]
    assert result["tail_rms_db"] < result["rms_db"] - 20, "doesn't decay (runaway feedback?)"
