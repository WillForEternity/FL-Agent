"""FL Studio MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fl_studio_mcp.tools.app import register_app_tools
from fl_studio_mcp.tools.channels import register_channel_tools
from fl_studio_mcp.tools.dsp import register_dsp_tools
from fl_studio_mcp.tools.effects import register_effect_tools
from fl_studio_mcp.tools.instruments import register_instrument_tools
from fl_studio_mcp.tools.mixer import register_mixer_tools
from fl_studio_mcp.tools.piano_roll import register_piano_roll_tools
from fl_studio_mcp.tools.plugins import register_plugin_tools
from fl_studio_mcp.tools.transport import register_transport_tools

if TYPE_CHECKING:
    from fastmcp import FastMCP

__all__ = [
    "register_all_tools",
    "register_app_tools",
    "register_transport_tools",
    "register_mixer_tools",
    "register_channel_tools",
    "register_plugin_tools",
    "register_piano_roll_tools",
    "register_instrument_tools",
    "register_effect_tools",
    "register_dsp_tools",
]


def register_all_tools(mcp: FastMCP) -> None:
    """Register every tool module. Also called by fl_reload_tools after a reload."""
    register_transport_tools(mcp)
    register_mixer_tools(mcp)
    register_channel_tools(mcp)
    register_plugin_tools(mcp)
    register_piano_roll_tools(mcp)
    register_instrument_tools(mcp)
    register_effect_tools(mcp)
    register_dsp_tools(mcp)
    register_app_tools(mcp)
