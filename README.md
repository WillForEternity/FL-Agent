# FL-Agent

Let Claude work inside FL Studio: load and tune instruments and effects, write its own synths and effects in DSP code, build projects, and drive the app, while you play and make the creative calls.

FL-Agent is an [MCP](https://modelcontextprotocol.io) server plus a pair of FL Studio plugins. Claude Code (or any MCP client) talks to the server; the server talks to FL Studio through a virtual MIDI port and a controller script running inside FL.

## What it can do

- **Control FL Studio:** transport and tempo, mixer, Channel Rack, step sequencer, plugin parameters, Piano Roll.
- **Load plugins:** add any installed instrument to the Channel Rack (FL's scripting API can't do this on its own).
- **Write custom DSP:** Claude writes synths and effects as [JSFX](https://www.reaper.fm/sdk/js/) scripts that run inside the bundled **FL-Agent FX** and **FL-Agent instrument** plugins. Every control is automatable, and edits hot-reload while you play.
- **Check sound before you hear it:** an offline renderer measures every script for clipping, silence, NaNs, DC offset, stereo width and runaway feedback.
- **Run the app:** open, save, start from a template, restart, with a guard that refuses to discard unsaved work.

An [example](examples/build_future_bass_palette.py) builds a 12-track future-bass sound palette (custom supersaw, sub, vocal-chop synth, drums, effects) in one command.

## Requirements

- macOS (Apple Silicon or Intel). The core MIDI tools also work on Windows with loopMIDI, but plugin loading, custom DSP builds and app control are macOS-only.
- FL Studio 20.7 or later (tested with FL Studio 2026, Fruity Edition)
- [uv](https://docs.astral.sh/uv/), CMake and the Xcode Command Line Tools (`brew install uv cmake`, `xcode-select --install`)
- [Claude Code](https://claude.com/claude-code) or another MCP client

## Quick start

```bash
git clone <this repo> FL-Agent && cd FL-Agent
./scripts/install.sh
```

The installer sets up the server, installs the FL Studio scripts, builds the plugins and registers the server with Claude Code. Then finish the one-time FL Studio setup in [docs/getting-started.md](docs/getting-started.md).

## Documentation

| Doc | Contents |
|---|---|
| [Getting started](docs/getting-started.md) | Installation and one-time FL Studio setup |
| [Architecture](docs/architecture.md) | How the pieces fit together, and why |
| [Tool reference](docs/tools.md) | Every MCP tool (generated from the code) |
| [Custom DSP](docs/custom-dsp.md) | Writing JSFX for FL-Agent, the script library, the offline renderer |
| [Development](docs/development.md) | Repo layout, tests, building, contributing |
| [Troubleshooting](docs/troubleshooting.md) | Common problems and known limitations |

## Licence

Apache-2.0 (see [LICENSE](LICENSE)), except files from the upstream [fl-studio-mcp](https://github.com/karl-andres/fl-studio-mcp) server, which remain MIT. The plugins are built from [ysfx](https://github.com/JoepVanlier/ysfx) (Apache-2.0) with JUCE; see [NOTICE](NOTICE) for details and for the licence terms that apply to distributing built plugins.

FL Studio is a trademark of Image-Line Software. FL-Agent is not affiliated with Image-Line.
