# SPDX-License-Identifier: Apache-2.0
"""Tests for the plugin database lookup (uses a fake database on disk)."""

import pytest

from fl_studio_mcp.utils import plugin_db


@pytest.fixture
def fake_db(tmp_path, monkeypatch):
    user = tmp_path / "user"
    app = tmp_path / "app"
    files = [
        user / "Generators/Misc/FL Keys.fst",
        user / "Effects/Delay reverb/Fruity Reeverb 2.fst",
        user / "Installed/Effects/VST3/FL-Agent FX.fst",
        app / "Generators/Misc/FL Keys.fst",  # duplicate: user copy wins
        app / "Generators/Synth classic/3x Osc.fst",
    ]
    for f in files:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"FLhd")

    def dirs(kind):
        return [user / kind, user / "Installed" / kind, app / kind]

    monkeypatch.setattr(plugin_db, "_db_dirs", dirs)
    return user, app


def test_finds_builtin_and_installed_plugins(fake_db):
    names = {p["name"] for p in plugin_db.list_plugins("Effects")}
    assert names == {"Fruity Reeverb 2", "FL-Agent FX"}


def test_user_database_takes_precedence(fake_db):
    user, _ = fake_db
    path, _ = plugin_db.resolve_plugin("Generators", "FL Keys")
    assert path == user / "Generators/Misc/FL Keys.fst"


def test_lookup_is_case_insensitive(fake_db):
    path, _ = plugin_db.resolve_plugin("Generators", "3X OSC")
    assert path is not None and path.stem == "3x Osc"


def test_unknown_name_returns_suggestions(fake_db):
    path, suggestions = plugin_db.resolve_plugin("Effects", "reeverb")
    assert path is None
    assert suggestions == ["Fruity Reeverb 2"]


def test_query_filters_by_category(fake_db):
    result = plugin_db.list_plugins("Generators", "synth classic")
    assert [p["name"] for p in result] == ["3x Osc"]
