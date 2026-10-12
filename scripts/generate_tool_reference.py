# SPDX-License-Identifier: Apache-2.0
"""Generate docs/tools.md from the MCP server's registered tools.

Usage (from the repo root):
    cd fl-studio-mcp && uv run python ../scripts/generate_tool_reference.py

The reference lists every tool with its parameters and docstring, grouped by
module. tests/test_tool_reference.py fails if the committed file is stale.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "tools.md"

GROUPS = {
    "server": "Connection and reload",
    "transport": "Transport and tempo",
    "mixer": "Mixer",
    "channels": "Channel Rack",
    "plugins": "Plugin parameters",
    "piano_roll": "Piano Roll",
    "instruments": "Loading instruments",
    "effects": "Loading effects",
    "dsp": "Custom DSP (JSFX)",
    "app": "App control (macOS)",
}


def _group_of(tool) -> str:
    module = getattr(tool.fn, "__module__", "") or ""
    return module.rsplit(".", 1)[-1]


def _params(tool) -> str:
    props = (tool.parameters or {}).get("properties", {})
    required = set((tool.parameters or {}).get("required", []))
    parts = []
    for name in props:
        if name == "ctx":
            continue
        parts.append(name if name in required else f"{name}?")
    return ", ".join(parts)


async def build() -> str:
    from fl_studio_mcp.server import mcp

    tools = sorted(await mcp.list_tools(), key=lambda t: t.name)
    by_group: dict[str, list] = {}
    for tool in tools:
        by_group.setdefault(_group_of(tool), []).append(tool)

    lines = [
        "# Tool reference",
        "",
        "Generated from the server code by `scripts/generate_tool_reference.py`; don't edit by",
        "hand. Parameters marked `?` are optional. "
        f"{len(tools)} tools.",
        "",
    ]
    for key, title in GROUPS.items():
        group = by_group.pop(key, [])
        if not group:
            continue
        lines += [f"## {title}", "", "| Tool | Parameters | Description |", "|---|---|---|"]
        for tool in group:
            doc = inspect.cleandoc(tool.description or "").split("\n\n")[0].replace("\n", " ")
            lines.append(f"| `{tool.name}` | {_params(tool) or '–'} | {doc.replace('|', '/')} |")
        lines.append("")
    if by_group:
        raise SystemExit(f"Tools in unknown modules, add them to GROUPS: {sorted(by_group)}")
    return "\n".join(lines)


def main() -> None:
    text = asyncio.run(build())
    if "--check" in sys.argv:
        if not OUTPUT.exists() or OUTPUT.read_text() != text:
            raise SystemExit(f"{OUTPUT} is out of date; run scripts/generate_tool_reference.py")
        return
    OUTPUT.write_text(text)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
