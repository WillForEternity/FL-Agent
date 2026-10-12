# SPDX-License-Identifier: Apache-2.0
"""docs/tools.md must match the registered tools (regenerate with the script if this fails)."""

import asyncio
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "generate_tool_reference.py"


def test_tool_reference_is_up_to_date():
    spec = importlib.util.spec_from_file_location("generate_tool_reference", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected = asyncio.run(module.build())
    assert module.OUTPUT.read_text() == expected, (
        "docs/tools.md is stale: run `uv run python ../scripts/generate_tool_reference.py`"
    )
