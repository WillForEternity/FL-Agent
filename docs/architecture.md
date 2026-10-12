# Architecture

```
 Claude Code / MCP client
          │  MCP (stdio)
          ▼
 FL-Agent MCP server (fl-studio-mcp/, Python)
   │  ① JSON request file + MIDI trigger note
   │     over the IAC Driver virtual port
   │  ② opens plugin-database presets (macOS `open`)
   │  ③ clicks FL's native menu bar (macOS Accessibility)
   │  ④ writes JSFX scripts and request files
   ▼
 FL Studio
   ├─ controller script (FLStudioMCP): runs commands through FL's Python API, writes a JSON response
   ├─ FL-Agent instrument / FL-Agent FX plugins: run JSFX scripts from dsp/
   └─ everything else in your project
```

## The command bridge (①)
FL Studio's scripting API is only available to scripts running inside FL, triggered by MIDI. So the server:
1. writes the command to `mcp_command.json` in FL's `Settings/Hardware/FLStudioMCP/` folder,
2. sends a trigger note on the IAC Driver port,
3. waits for the controller script (`fl_controller/device_FLStudioMCP.py`) to run the command and write `mcp_response.json`.

The request/response files are shared, so **only one client should drive FL at a time.**

Changes to the controller script take effect after FL Studio restarts (`fl_restart`, or `scripts/install.sh --controller-only` then restart).

## Loading plugins (②)
The scripting API can't create plugins. FL Studio does load a plugin when macOS asks it to open that plugin's preset file from FL's **plugin database** (`Presets/Plugin database/`, including `Installed/` for third-party plugins after a plugin scan):
- An **instrument** (generator) preset becomes a new Channel Rack channel. `fl_load_instrument` waits for it, then routes and names it.
- An **effect** preset always lands on **Master**, whatever track is selected or focused. Opening a saved *mixer track state* file the same way replaces Master's whole effect chain, so FL-Agent never does that.

## Custom DSP: the FL-Agent plugins
FL-Agent FX and FL-Agent instrument are a modified build of [ysfx](https://github.com/JoepVanlier/ysfx), a JSFX host, applied as `patches/ysfx-flagent.patch`. The changes:

| Change | Purpose |
|---|---|
| **Pending-script claim:** a new instance loads the script named in `~/Library/Application Support/FL-Agent/ysfx/pending.txt` (if under 30 s old) and deletes the file | Lets a tool choose what a freshly loaded instrument runs |
| **Assign by parameter:** a hidden host parameter, "FL-Agent assign". Setting it on one instance makes that instance load the script named in a matching request file | Targets one existing instance through FL's official API |
| **Hot reload:** a 250 ms timer reloads the script when its file changes, keeping control values | Edits are heard immediately |
| **Rebranding:** separate names, plugin codes and bundle ID | Can't clash with a stock ysfx install |

Every JSFX slider becomes an automatable plugin parameter, so the normal plugin tools tune them.

### Custom effects on a specific track
Because opened effects land on Master, effects use **assign by parameter**:
1. The track needs a blank FL-Agent FX in some slot. The FL-Agent template provides one in slot 10 of Inserts 1–16.
2. `fl_create_dsp_effect` / `fl_assign_dsp_effect` find that instance, look up "FL-Agent assign" **by name** (its index differs between projects), write the script path to `assign-<token>.txt`, and set the parameter to the token's value.
3. The plugin picks the request up within 250 ms, loads the script, deletes the file and resets the parameter; the tool waits for the file to disappear as confirmation.

FL rounds this parameter to two decimal places on its way to the plugin, so tokens are hundredths (`k / 100`), which survive the rounding exactly.

## App control (③)
FL's windows are custom-drawn and invisible to macOS Accessibility, but its **menu bar is native**. The app-control tools click menu items by name (never screen positions), read the window title for the open project, use `pgrep` for process state, and check readiness by asking the controller.

**Safety rule:** nothing that closes the current project runs while it has unsaved changes, unless the caller passes `discard_unsaved=true` (only with the user's agreement). Unsaved state comes from FL's own changed flag (`general.getProjectState`); if it can't be determined, it counts as unsaved.

FL's dialogs (save prompts, startup messages) are custom-drawn too, so FL-Agent can't read or answer them. When a launch stalls on one, the tools say so.

## Hot reload of the server
`fl_reload_tools` re-imports the tool modules in dependency order and re-registers their tools, after checking that every module compiles, so a typo can't take the working tools down. Edits to existing tools apply immediately. Newly added tools appear in the client's next session, and changes to `server.py` or the MIDI connection code need a new session.

## Design choices
- **Look things up by name, not index.** Plugin parameter indices, channel indices and slot numbers vary between projects.
- **Verify by reading back.** Tools confirm their effect (new channel present, request file consumed, changed flag cleared) instead of trusting that the command was sent.
- **Check audio offline first.** Custom DSP is rendered with `bin/flagent_render` before it's loaded into FL ([custom-dsp.md](custom-dsp.md)).
