# SPDX-License-Identifier: Apache-2.0
"""Tests for the custom DSP helpers (no FL Studio needed)."""

import math
import random

import pytest

from fl_studio_mcp.tools import dsp


def plugin_decode(value: float) -> int:
    """What processor.cpp computes: juce::roundToInt(float(value) * kAgentTokenScale)."""
    # FL Studio rounds the parameter to 2 decimals and the plugin reads a float
    received = float(f"{round(value, 2):.7g}")
    return math.floor(received * dsp.TOKEN_SCALE + 0.5)


def test_every_assign_token_survives_fl_rounding():
    for k in range(1, dsp.TOKEN_STEPS):
        value = k / dsp.TOKEN_STEPS
        assert plugin_decode(value) == round(value * dsp.TOKEN_SCALE), k


def test_new_assign_token_is_in_range_and_consistent():
    rng = random.Random(0)
    for _ in range(500):
        value, token = dsp.new_assign_token(rng)
        assert 0 < value < 1
        assert token == plugin_decode(value)


def test_assign_value_never_zero():
    # 0 means "no request" to the plugin
    rng = random.Random(1)
    assert all(dsp.new_assign_token(rng)[0] > 0 for _ in range(1000))


@pytest.mark.parametrize(
    ("name", "file"),
    [
        ("Petal Delay", "petal-delay.jsfx"),
        ("Glass Bloom!", "glass-bloom.jsfx"),
        ("  spaced  out  ", "spaced-out.jsfx"),
        ("FM_Bell 2", "fm-bell-2.jsfx"),
    ],
)
def test_script_path_slugs(name, file):
    assert dsp._script_path(name).name == file


def test_script_path_rejects_empty_names():
    with pytest.raises(ValueError):
        dsp._script_path("!!!")


def test_write_script_adds_desc_line(tmp_path, monkeypatch):
    monkeypatch.setattr(dsp, "DSP_DIR", tmp_path)
    path = dsp._write_script("Test FX", "@sample\nspl0 = spl0;\n")
    assert path.read_text().startswith("desc:Test FX\n")


def test_write_script_keeps_existing_desc(tmp_path, monkeypatch):
    monkeypatch.setattr(dsp, "DSP_DIR", tmp_path)
    code = "desc:Mine\n@sample\n"
    assert dsp._write_script("Other", code).read_text() == code
