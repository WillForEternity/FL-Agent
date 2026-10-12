# Getting started

Installing FL-Agent takes two parts: an install script, and a few one-time clicks in macOS and FL Studio that can't be scripted.

## 1. Prerequisites

| Need | How |
|---|---|
| macOS | FL-Agent's plugin loading, custom DSP and app control are macOS-only |
| FL Studio 20.7+ | Start it once before installing, so its settings folder exists |
| uv, CMake | `brew install uv cmake` |
| Xcode Command Line Tools | `xcode-select --install` |
| Claude Code | [claude.com/claude-code](https://claude.com/claude-code) (or any MCP client) |

## 2. Run the installer

```bash
./scripts/install.sh            # everything
./scripts/install.sh --no-plugins   # skip building the FL-Agent plugins
```

It is safe to re-run. It:
1. Installs the MCP server's Python environment (`uv sync`).
2. Copies the controller script into `~/Documents/Image-Line/FL Studio/Settings/Hardware/FLStudioMCP/` and the Piano Roll script into `…/Settings/Piano roll scripts/`.
3. Builds and installs the **FL-Agent FX** and **FL-Agent instrument** plugins (to `~/Library/Audio/Plug-Ins/VST3/`) and the offline renderer `bin/flagent_render`. The first build downloads ysfx and JUCE and takes about 10 minutes.
4. Registers the server with Claude Code as `fl-studio`, if the `claude` command is on your PATH. Otherwise it prints the command to run.

## 3. One-time FL Studio setup

### Virtual MIDI port
1. Open **Audio MIDI Setup** and choose **Window → Show MIDI Studio**.
2. Double-click **IAC Driver**, check **Device is online**, make sure a port (e.g. **Bus 1**) exists, and click **Apply**.

### Controller
1. Restart FL Studio.
2. **Options → MIDI settings**, Input list: select **IAC Driver Bus 1**, set **Controller type** to **FL Studio MCP Controller**, and click **Enable**.
3. A MIDI keyboard can stay enabled alongside it (as a generic controller); it plays whichever channel is selected.

### Plugins
**Options → Manage plugins → Find installed plugins.** FL-Agent FX and FL-Agent instrument should appear in the list.

### Permissions
The app-control tools (save, open, restart, templates) drive FL's menu bar. Give the app that runs Claude Code (e.g. Terminal or VS Code) **Accessibility** permission in **System Settings → Privacy & Security → Accessibility**.

### Project template
Custom effects run in an FL-Agent FX that must already be in the target mixer slot (see [architecture](architecture.md#custom-effects-on-a-specific-track)). A template puts one on every track, so Claude never needs per-track setup:
1. **File → New from template → Minimal → Empty.**
2. In the Mixer, select **Insert 1**, then drag **FL-Agent FX** from the Browser's Plugins tab onto its **slot 10**. Close the plugin window. Repeat for Inserts 2–16.
3. **File → Save as template…** and name it **FL-Agent**.

Claude can then start projects with `fl_new_project(["FL-Agent"])`. A blank FL-Agent FX passes audio through unchanged, so the template is transparent until a script is assigned.

### Piano Roll (optional)
Writing notes into the Piano Roll uses a Piano Roll script triggered by a keystroke. Run it once by hand: open the Piano Roll (F7), then **Tools → Scripting → ComposeWithLLM**.

## 4. Check it works
Start a new Claude Code session in this folder and ask Claude to check the FL Studio connection (`fl_connection_status`) and list your channels. Then try something like "load FL Keys on mixer track 2" or "write me a soft FM bell and load it".

If something doesn't respond, see [troubleshooting](troubleshooting.md).
