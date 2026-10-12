# Tool reference

Generated from the server code by `scripts/generate_tool_reference.py`; don't edit by
hand. Parameters marked `?` are optional. 80 tools.

## Connection and reload

| Tool | Parameters | Description |
|---|---|---|
| `fl_connect` | – | Connect or reconnect to FL Studio via MIDI. |
| `fl_connection_status` | – | Get the current FL Studio connection status. |
| `fl_reload_tools` | – | Reload the tool modules so edits to their code apply without a new session. |

## Transport and tempo

| Tool | Parameters | Description |
|---|---|---|
| `fl_get_song_length` | – | Get the total length of the current song/pattern. |
| `fl_get_tempo` | – | Get the project tempo in BPM. |
| `fl_get_transport_status` | – | Get current transport status including playback and recording state. |
| `fl_play` | – | Start or pause FL Studio playback. |
| `fl_record` | – | Toggle recording mode in FL Studio. |
| `fl_set_loop_mode` | mode | Set the loop mode between pattern and song. |
| `fl_set_playback_speed` | speed | Set the playback speed multiplier. |
| `fl_set_song_position` | position, mode? | Set the playback position in FL Studio. |
| `fl_set_tempo` | bpm | Set the project tempo. |
| `fl_stop` | – | Stop FL Studio playback completely. |

## Mixer

| Tool | Parameters | Description |
|---|---|---|
| `fl_arm_track` | track | Toggle the recording arm state of a mixer track. |
| `fl_get_all_mixer_tracks` | include_empty? | Get information about all mixer tracks. |
| `fl_get_mixer_track_count` | – | Get the total number of mixer tracks available. |
| `fl_get_mixer_track_info` | track | Get detailed information about a specific mixer track. |
| `fl_mute_track` | track, muted? | Mute or unmute a mixer track. |
| `fl_set_stereo_separation` | track, separation | Set the stereo separation of a mixer track. |
| `fl_set_track_color` | track, red, green, blue | Set the color of a mixer track. |
| `fl_set_track_name` | track, name | Set the name of a mixer track. |
| `fl_set_track_pan` | track, pan | Set the pan position of a mixer track. |
| `fl_set_track_volume` | track, volume | Set the volume of a mixer track. |
| `fl_solo_track` | track, solo?, mode? | Solo or unsolo a mixer track. |

## Channel Rack

| Tool | Parameters | Description |
|---|---|---|
| `fl_get_all_channels` | – | Get information about all channels in the channel rack. |
| `fl_get_channel_count` | global_count? | Get the number of channels in the channel rack. |
| `fl_get_channel_info` | index, use_global_index? | Get detailed information about a channel. |
| `fl_get_grid_bit` | channel, position | Get whether a step is active in the step sequencer. |
| `fl_get_selected_channel` | – | Get information about the currently selected channel. |
| `fl_get_step_sequence` | channel, steps? | Get the step sequence pattern for a channel. |
| `fl_mute_channel` | index, muted? | Mute or unmute a channel. |
| `fl_route_channel_to_mixer` | channel_index, mixer_track | Route a channel to a specific mixer track. |
| `fl_select_channel` | index, select? | Select or deselect a channel. |
| `fl_select_one_channel` | index | Select only one channel, deselecting all others. |
| `fl_set_channel_color` | index, red, green, blue | Set the color of a channel. |
| `fl_set_channel_name` | index, name | Set the name of a channel. |
| `fl_set_channel_pan` | index, pan | Set the pan position of a channel. |
| `fl_set_channel_volume` | index, volume | Set the volume of a channel. |
| `fl_set_grid_bit` | channel, position, value | Set a step in the step sequencer on or off. |
| `fl_set_step_sequence` | channel, pattern | Set a complete step sequence pattern for a channel. |
| `fl_solo_channel` | index, solo? | Solo or unsolo a channel. |
| `fl_trigger_note` | channel, note, velocity?, midi_channel? | Trigger a MIDI note on a channel (real-time, does NOT persist to pattern). |

## Plugin parameters

| Tool | Parameters | Description |
|---|---|---|
| `fl_get_plugin_color` | index, slot_index?, use_global_index? | Get the color of a plugin. |
| `fl_get_plugin_name` | index, slot_index?, use_global_index? | Get the name of a plugin. |
| `fl_get_plugin_param_count` | index, slot_index?, use_global_index? | Get the number of parameters a plugin has. |
| `fl_get_plugin_param_value` | param_index, plugin_index, slot_index?, use_global_index? | Get the value of a specific plugin parameter. |
| `fl_get_plugin_params` | index, slot_index?, use_global_index?, max_params? | Get all parameters of a plugin with their current values. |
| `fl_get_preset_count` | index, slot_index?, use_global_index? | Get the number of presets available for a plugin. |
| `fl_is_plugin_valid` | index, slot_index?, use_global_index? | Check if a plugin exists at the given location. |
| `fl_next_preset` | index, slot_index?, use_global_index? | Switch to the next preset for a plugin. |
| `fl_prev_preset` | index, slot_index?, use_global_index? | Switch to the previous preset for a plugin. |
| `fl_set_plugin_param_value` | param_index, value, plugin_index, slot_index?, use_global_index? | Set the value of a plugin parameter. |

## Piano Roll

| Tool | Parameters | Description |
|---|---|---|
| `fl_clear_piano_roll` | auto_trigger? | Clear all notes from the FL Studio piano roll. |
| `fl_clear_request_queue` | – | Clear any pending note requests without executing them. |
| `fl_delete_notes` | notes, auto_trigger? | Delete specific notes from the FL Studio piano roll. |
| `fl_get_piano_roll_info` | – | Get information about the Piano Roll integration status. |
| `fl_get_piano_roll_state` | – | Get the current state of notes in the FL Studio piano roll. |
| `fl_send_chord` | midi_notes, time?, duration?, velocity?, auto_trigger? | Add a chord (multiple simultaneous notes) to the FL Studio piano roll. |
| `fl_send_notes` | notes, mode?, auto_trigger? | Add or replace notes in the FL Studio piano roll. |
| `fl_trigger_script` | – | Manually trigger FL Studio to process pending note requests. |

## Loading instruments

| Tool | Parameters | Description |
|---|---|---|
| `fl_list_instruments` | query? | List instruments (generator plugins) that fl_load_instrument can load. |
| `fl_load_instrument` | name, mixer_track?, channel_name? | Load an instrument into a new Channel Rack channel. |

## Loading effects

| Tool | Parameters | Description |
|---|---|---|
| `fl_get_mixer_slots` | track | List the effects loaded in a mixer track's 10 slots. |
| `fl_list_effects` | query? | List effect plugins that fl_load_effect can load. |
| `fl_load_effect` | name, mixer_track | Load an effect into a mixer slot. |

## Custom DSP (JSFX)

| Tool | Parameters | Description |
|---|---|---|
| `fl_assign_dsp_effect` | name, mixer_track, slot_index? | Run an existing custom effect script in an FL-Agent FX on a mixer track. |
| `fl_create_dsp_effect` | name, code, mixer_track, slot_index? | Write a JSFX effect and run it in an FL-Agent FX on a mixer track. |
| `fl_create_dsp_instrument` | name, code, mixer_track? | Write a JSFX instrument and load it into a new Channel Rack channel. |
| `fl_list_dsp` | – | List the custom JSFX effects and instruments written so far. |
| `fl_load_dsp_instrument` | name, mixer_track? | Load an existing custom instrument script into a new Channel Rack channel. |
| `fl_read_dsp` | name | Read the JSFX source of a custom effect or instrument. |
| `fl_update_dsp` | name, code | Replace the code of an existing custom effect or instrument. |

## App control (macOS)

| Tool | Parameters | Description |
|---|---|---|
| `fl_launch` | project? | Start FL Studio, optionally opening a project, and wait until it's ready. |
| `fl_list_templates` | – | List FL Studio's project templates (File > New from template). |
| `fl_new_project` | template?, discard_unsaved? | Start a new project, optionally from a template. |
| `fl_open_project` | path, discard_unsaved? | Open a project file in FL Studio. |
| `fl_project_status` | – | Report whether FL Studio is running, the open project, and unsaved changes. |
| `fl_quit` | discard_unsaved? | Quit FL Studio. |
| `fl_restart` | reopen_project?, discard_unsaved? | Quit and relaunch FL Studio, e.g. to load an updated controller script or plugin. |
| `fl_save_project` | – | Save the open project (File > Save). |
