# FL-Agent MCP server

The MCP server half of [FL-Agent](../README.md): it lets Claude (or any MCP client) control FL Studio. See the [main README](../README.md) and the [docs](../docs/README.md) for setup and usage.

| Path | Contents |
|---|---|
| `src/fl_studio_mcp/server.py` | Server entry point and core tools |
| `src/fl_studio_mcp/tools/` | Tool modules (one per area), registered in `tools/__init__.py` |
| `src/fl_studio_mcp/utils/` | MIDI bridge, plugin database lookup, macOS automation |
| `fl_controller/device_FLStudioMCP.py` | Controller script that runs inside FL Studio |
| `scripts/ComposeWithLLM.pyscript` | Piano Roll script that runs inside FL Studio |
| `tests/` | Tests (`uv run pytest`); none need FL Studio |

## Development

```bash
uv sync
uv run pytest -q
uv run ruff check src tests
```

## Origin and licence

Based on [karl-andres/fl-studio-mcp](https://github.com/karl-andres/fl-studio-mcp) (MIT; commit `202b7a2`), which builds on [calvinw/fl-studio-mcp](https://github.com/calvinw/fl-studio-mcp). Files from upstream remain under the MIT licence in `LICENSE`; files added by FL-Agent carry an `SPDX-License-Identifier: Apache-2.0` header and are covered by the repository's [Apache-2.0 licence](../LICENSE). See [NOTICE](../NOTICE).
