"""FL Studio MCP Server - Control FL Studio via Model Context Protocol.

This MCP server provides tools to control FL Studio through two mechanisms:
1. MIDI + JSON - Real-time control of mixer, transport, channels, and plugins
2. Piano Roll Scripts - Persistent note placement via JSON + keystroke triggering

Requirements:
- FL Studio 20.7+ running
- FLStudioMCP controller script installed (run: ./scripts/setup_mac.sh)
- On Mac: IAC Driver enabled in Audio MIDI Setup
- On Windows: loopMIDI virtual MIDI ports configured
- For piano roll: ComposeWithLLM.pyscript installed in FL Studio

Limitations:
- Plugins can't be loaded through the scripting API; the instrument, effect
  and DSP tools work around this on macOS by opening plugin-database presets
- Cannot create new patterns programmatically
"""

from __future__ import annotations

import mcp.types as mcp_types
from fastmcp import Context, FastMCP

from fl_studio_mcp.reload import reload_tools
from fl_studio_mcp.tools import register_all_tools
from fl_studio_mcp.utils.connection import get_connection, reset_connection

# Create the MCP server
mcp = FastMCP(
    name="fl-studio-mcp",
    instructions="""
FL Studio MCP Server - Control FL Studio from AI assistants.

This server provides tools to control FL Studio through its Python scripting API.
FL Studio must be running with the FLStudioMCP MIDI controller enabled.

Available tool categories:
- Transport: Play, stop, record, tempo, position control
- Mixer: Volume, pan, mute, solo, track management
- Channels: Channel info, note triggering, step sequencer
- Plugins: Parameter control, preset navigation
- Instruments: List and load generators into new channels (macOS)
- Effects: List and load effects into mixer slots, then tune via plugin tools (macOS)
- Custom DSP: Write JSFX effects/instruments that run in the FL-Agent plugins
- App control: project status, save, open, new from template, quit, launch,
  restart (macOS). These refuse to drop unsaved changes unless the user agreed
  and discard_unsaved=true is passed.
- fl_reload_tools: apply edits to the tool code without a new session

Important limitations:
1. Plugins load by opening plugin-database presets (macOS only)
2. Cannot create new patterns programmatically
3. Note triggering (fl_trigger_note) is real-time only - notes won't persist
   unless FL Studio is recording. Use step sequencer (fl_set_grid_bit) for
   persistent drum patterns.
""",
)


# Register connection status resource
@mcp.resource("fl://status")
def get_fl_status() -> str:
    """Get FL Studio connection status."""
    conn = get_connection()
    if conn.is_connected:
        return "Connected to FL Studio via MIDI"
    else:
        return f"Not connected: {conn.connection_error}"


@mcp.resource("fl://project")
def get_project_info() -> dict:
    """Get current FL Studio project information."""
    conn = get_connection()

    if not conn.is_connected:
        return {"error": conn.connection_error}

    try:
        result = conn.send_command("transport.getStatus")
        if not result.get("success", False) and "error" in result:
            return {"error": result["error"]}

        return {
            "is_playing": result.get("is_playing", False),
            "is_recording": result.get("is_recording", False),
            "position": result.get("position", ""),
            "loop_mode": result.get("loop_mode", "pattern"),
        }
    except Exception as e:
        return {"error": str(e)}


# Connection management tools
@mcp.tool()
def fl_connect() -> str:
    """Connect or reconnect to FL Studio via MIDI.

    Use this tool to:
    - Check if FL Studio is connected
    - Retry connection after starting FL Studio
    - Reconnect if the connection was lost

    Returns the connection status.
    """
    # Reset connection state to force a fresh connection attempt
    reset_connection()

    conn = get_connection()
    try:
        conn.ensure_connected()
    except RuntimeError as e:
        return f"Connection failed: {e}"
    return "Successfully connected to FL Studio via MIDI!"


@mcp.tool()
def fl_connection_status() -> dict:
    """Get the current FL Studio connection status.

    Returns information about whether FL Studio is connected
    and any error messages if not.
    """
    conn = get_connection()
    # Eagerly attempt a connection so the reported status reflects actual
    # reachability rather than the lazily-initialized flag.
    try:
        conn.ensure_connected()
    except RuntimeError:
        pass
    status = conn.get_status()
    return {
        "connected": status.get("connected", False),
        "port_name": status.get("port_name"),
        "available_ports": status.get("available_ports", []),
        "error": status.get("error"),
    }


@mcp.tool()
async def fl_reload_tools(ctx: Context) -> dict:
    """Reload the tool modules so edits to their code apply without a new session.

    Compiles every module first and changes nothing if any has an error.
    Edits to server.py or the MIDI connection code still need a new session,
    and edits to the controller script need an FL restart (fl_restart).
    """
    result = await reload_tools(mcp)
    if result.get("reloaded"):
        # Tell the client to fetch the updated tool list
        await ctx.send_notification(mcp_types.ToolListChangedNotification())
    return result


register_all_tools(mcp)


def main():
    """Run the FL Studio MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
