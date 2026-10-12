# Troubleshooting

## Common problems

| Symptom | Fix |
|---|---|
| "Not connected to FL Studio" / commands time out | FL Studio is running; **IAC Driver** is online in Audio MIDI Setup; in FL's MIDI settings, IAC Driver Bus 1 is enabled with controller type **FL Studio MCP Controller**. Check **View → Script output** in FL for errors |
| The server picks the wrong MIDI port | With no IAC port, the server falls back to the first port it finds (often a keyboard). Turn the IAC Driver on |
| "Unknown action: …" | FL is running an older controller script: `./scripts/install.sh --controller-only`, then restart FL |
| FL Studio MCP Controller missing from the controller list | In MIDI settings, click **Update MIDI scripts**, then **Refresh device list** |
| FL-Agent FX / instrument not found | Run `./scripts/build-plugins.sh`, then **Options → Manage plugins → Find installed plugins** |
| A custom effect isn't assigned ("No FL-Agent FX on mixer track N") | Add a blank FL-Agent FX to that track, or start the project from the FL-Agent template |
| Custom script loads but is silent | Check it offline: `bin/flagent_render dsp/<name>.jsfx --notes 60` (instrument) or `--input pluck` (effect). Run the script tests (case-clash lint) |
| `fl_launch` / `fl_restart` says FL is showing a dialog | FL's dialogs can't be read or answered automatically; answer it in FL |
| App-control tools fail with "not allowed assistive access" | Give the app running Claude Code Accessibility permission (System Settings → Privacy & Security → Accessibility) |
| Tools refuse to close a project you just opened | FL marks a project as changed right after loading it. Save it (`fl_save_project`) to clear the flag |
| Build fails with `ld: tapi error: malformed file` | Your default macOS SDK doesn't match the linker; `build-plugins.sh` picks a working SDK automatically. If none works, reinstall the Command Line Tools |
| New tools added during a session aren't available | They appear in the next Claude Code session; existing tools update immediately with `fl_reload_tools` |
| Piano Roll notes don't appear | Run **Tools → Scripting → ComposeWithLLM** once by hand in the Piano Roll; check Accessibility permission |

## Known limitations
- **One driver at a time.** Clients share the command/response files; two sessions controlling one FL Studio will interfere.
- **Effects opened from outside FL land on Master.** Custom effects work around this by assigning scripts to an FL-Agent FX already on the track; built-in FL effects still have to be added to other tracks by hand.
- **No plugin removal and no pattern creation** through FL's scripting API.
- **FL's windows and dialogs are invisible to automation.** Only the menu bar can be driven.
- **Some FL plugins load in demo mode** depending on your FL Studio edition.
- **macOS only** for plugin loading, custom DSP builds and app control.
