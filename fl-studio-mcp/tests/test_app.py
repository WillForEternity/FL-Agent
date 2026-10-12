# SPDX-License-Identifier: Apache-2.0
"""Tests for the app-control safety logic and AppleScript helpers (no FL Studio needed)."""

import pytest

from fl_studio_mcp.tools import app
from fl_studio_mcp.utils import macos_ui


@pytest.mark.parametrize(
    ("text", "literal"),
    [
        ("Save", '"Save"'),
        ('Say "hi"', '"Say \\"hi\\""'),
        ("back\\slash", '"back\\\\slash"'),
    ],
)
def test_applescript_string_escapes(text, literal):
    assert macos_ui.applescript_string(text) == literal


def test_click_menu_needs_a_menu_item():
    with pytest.raises(ValueError):
        macos_ui.click_menu(["File"])


def test_guard_allows_saved_project(monkeypatch):
    monkeypatch.setattr(app, "unsaved_changes", lambda: False)
    assert app.guard_unsaved(discard_unsaved=False) is None


def test_guard_blocks_unsaved_project(monkeypatch):
    monkeypatch.setattr(app, "unsaved_changes", lambda: True)
    assert "unsaved changes" in app.guard_unsaved(discard_unsaved=False)["error"]


def test_guard_blocks_when_state_unknown(monkeypatch):
    # Not knowing must be treated as unsafe
    monkeypatch.setattr(app, "unsaved_changes", lambda: None)
    assert "error" in app.guard_unsaved(discard_unsaved=False)


def test_guard_respects_explicit_discard(monkeypatch):
    monkeypatch.setattr(app, "unsaved_changes", lambda: True)
    assert app.guard_unsaved(discard_unsaved=True) is None


def test_quit_refuses_unsaved_without_touching_fl(monkeypatch):
    monkeypatch.setattr(macos_ui, "is_running", lambda: True)
    monkeypatch.setattr(app, "unsaved_changes", lambda: True)

    def must_not_quit():
        raise AssertionError("quit requested despite unsaved changes")

    monkeypatch.setattr(macos_ui, "request_quit", must_not_quit)
    assert "error" in app.quit_fl(discard_unsaved=False)


def test_quit_when_not_running(monkeypatch):
    monkeypatch.setattr(macos_ui, "is_running", lambda: False)
    assert app.quit_fl()["quit"] is True


def test_project_name_from_window_title(monkeypatch):
    monkeypatch.setattr(
        macos_ui, "project_window_title", lambda: "Project_1.flp - FL Studio 2026"
    )
    assert app.project_name() == "Project_1.flp"


def test_launch_rejects_missing_project(tmp_path):
    assert "error" in app.launch_fl(str(tmp_path / "missing.flp"))


def test_request_quit_tolerates_fl_cancel_reply(monkeypatch):
    # FL replies -128 to the quit event even when it quits
    def reply(*_args, **_kwargs):
        raise macos_ui.UIAutomationError("execution error: User canceled. (-128)")

    monkeypatch.setattr(macos_ui, "run_applescript", reply)
    monkeypatch.setattr(macos_ui, "find_app", lambda: macos_ui.Path("/Applications/FL.app"))
    macos_ui.request_quit()  # must not raise


def test_request_quit_reports_other_errors(monkeypatch):
    def reply(*_args, **_kwargs):
        raise macos_ui.UIAutomationError("not allowed assistive access")

    monkeypatch.setattr(macos_ui, "run_applescript", reply)
    monkeypatch.setattr(macos_ui, "find_app", lambda: macos_ui.Path("/Applications/FL.app"))
    with pytest.raises(macos_ui.UIAutomationError):
        macos_ui.request_quit()
