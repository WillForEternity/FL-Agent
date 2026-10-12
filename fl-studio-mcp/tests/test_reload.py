# SPDX-License-Identifier: Apache-2.0
"""Tests for fl_reload_tools (in-process, no FL Studio needed)."""

import pytest
from fastmcp import Client

from fl_studio_mcp import reload
from fl_studio_mcp.server import mcp

# Async tests run on anyio's pytest plugin (installed with fastmcp)
pytestmark = pytest.mark.anyio


async def tool_names() -> set[str]:
    async with Client(mcp) as client:
        return {t.name for t in await client.list_tools()}


async def test_reload_keeps_every_tool():
    before = await tool_names()
    result = await reload.reload_tools(mcp)
    assert result["reloaded"] is True
    assert result["added"] == [] and result["removed"] == []
    assert await tool_names() == before


async def test_reloaded_tools_still_run():
    await reload.reload_tools(mcp)
    async with Client(mcp) as client:
        result = await client.call_tool("fl_list_dsp", {})
    assert "scripts" in result.data


async def test_compile_error_leaves_tools_untouched(monkeypatch):
    before = await tool_names()
    monkeypatch.setattr(reload, "check_sources", lambda: ["tools.dsp: invalid syntax"])
    result = await reload.reload_tools(mcp)
    assert result == {"reloaded": False, "errors": ["tools.dsp: invalid syntax"]}
    assert await tool_names() == before


def test_check_sources_reports_syntax_errors(tmp_path, monkeypatch):
    (tmp_path / "broken_mod.py").write_text("def f(:\n")
    (tmp_path / "fine_mod.py").write_text("x = 1\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    errors = reload.check_sources(("fine_mod", "broken_mod"))
    assert len(errors) == 1 and errors[0].startswith("broken_mod:")


def test_reload_order_covers_every_tool_module():
    from pathlib import Path

    tools_dir = Path(reload.__file__).parent / "tools"
    modules = {f"fl_studio_mcp.tools.{p.stem}" for p in tools_dir.glob("*.py")}
    modules.discard("fl_studio_mcp.tools.__init__")
    assert modules <= set(reload.RELOAD_ORDER)


@pytest.fixture
def anyio_backend():
    return "asyncio"
