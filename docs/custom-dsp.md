# Custom DSP

FL-Agent lets Claude write its own synths and effects as **JSFX** scripts (the audio scripting language from REAPER) and run them in FL Studio through the **FL-Agent instrument** and **FL-Agent FX** plugins. This page covers the workflow, the conventions scripts must follow, the included library, and offline checking.

## Workflow

1. **Write** the script into `dsp/<name>.jsfx` (or let `fl_create_dsp_instrument` / `fl_create_dsp_effect` write it).
2. **Check it offline** with `bin/flagent_render` and the script tests (below). Don't load untested DSP into a session someone is listening to.
3. **Load it:**
   - Instrument: `fl_load_dsp_instrument(name, mixer_track)` adds a new channel running the script.
   - Effect: `fl_assign_dsp_effect(name, mixer_track)` runs it in the FL-Agent FX already on that track ([why](architecture.md#custom-effects-on-a-specific-track)).
4. **Tune** with `fl_get_plugin_params` / `fl_set_plugin_param_value`: each `sliderN` is a parameter, in order.
5. **Edit** with `fl_update_dsp`: every instance running the script reloads it within about 250 ms and keeps its control values.

Scripts live in `dsp/` at the repo root; set `FL_AGENT_DSP_DIR` to use another folder.

## Script anatomy

```
desc:Name - one-line summary
// SPDX-License-Identifier: Apache-2.0
// What it does and the maths behind it.
slider1:0.5<0,1,0.01>Volume        // default<min,max,step>Label
@init      // runs on load and sample-rate change: allocate memory, set state
@slider    // runs when a control changes: derive coefficients
@block     // runs once per audio block: read MIDI with midirecv()
@sample    // runs per sample: read/write spl0 (left) and spl1 (right)
```

Instruments read MIDI in `@block` and write audio. Effects process `spl0`/`spl1`. The host provides `srate`, `tempo`, `beat_position` and `play_state`.

## Conventions

These are enforced by tests where possible. Each comes from a real bug.

| Rule | Why |
|---|---|
| **Never use two names that differ only in case.** EEL2 identifiers are case-insensitive: `U` and `u` are the same variable | A unison count named `U` was reset by a loop counter `u`, and the synth rendered silence. Linted |
| **Parenthesise conditionals.** Write `(a > b) ? (x = 1);` and `y = ((c) ? 1 : 0);` | `?:` binds looser than `=`, which silently changes what gets assigned |
| **Normalise resonant filters.** A state-variable band-pass output peaks at gain Q; multiply by 1/Q | A Q of 9 formant filter clipped at +11 dBFS |
| **Keep headroom.** Single notes around −12 dBFS, dense chords below −3 dBFS. Put a soft limiter (`tanh`) on anything that can resonate or stack | Mixing starts from sensible levels; extreme settings can't clip. Tested |
| **Keep low end mono.** Basses output identical channels | Mono compatibility |
| **Smooth anything that jumps.** Use short ramps or one-pole smoothing for gain changes and note starts | Avoids clicks |
| **Anti-alias oscillators** (PolyBLEP or better) | Naive saws alias badly at high notes |
| **Document the maths** in the header comment | The script is the spec |

## Script library

| Script | Type | Summary |
|---|---|---|
| `bloom-saw` | Instrument | 8-voice supersaw: 7 anti-aliased saws per note, symmetric detune and stereo spread, TPT state-variable low-pass with filter envelope; mod wheel, pitch bend, sustain pedal |
| `root-sub` | Instrument | Mono sine sub bass, last-note priority, exponential glide, tanh drive for harmonics |
| `fairy-vox` | Instrument | Formant "vocal chop" synth: saw and breath through three band-pass formants, vowel morph and per-note vowel cycling, scoop, delayed vibrato, per-vowel loudness compensation |
| `glass-bloom` | Instrument | Two-operator FM bell with inharmonic ratio; brightness decays faster than volume |
| `bloom-kick` | Instrument | Pitch-swept sine kick with noise click and drive |
| `snap-clap` | Instrument | Multi-burst band-passed noise clap with a tonal body |
| `silk-hats` | Instrument | 808-style hi-hats (six square waves + noise); closed below D4, open from D4 |
| `wind-riser` | Instrument | Tempo-synced noise sweep for build-ups, while a key is held |
| `petal-delay` | Effect | Ping-pong delay with tape wow; each repeat is darker and softly saturated |
| `petal-pump` | Effect | Tempo-synced "sidechain" volume pump, click-free; free-runs when stopped |
| `moss-verb` | Effect | Freeverb-style stereo reverb with pre-delay, low cut and a wet-path limiter |

Each file's header explains its maths and controls.

## Offline checking: `bin/flagent_render`

A headless JSFX host built from the same engine as the plugins (`scripts/build-plugins.sh` builds it). It renders a script and prints JSON.

```bash
bin/flagent_render dsp/bloom-saw.jsfx --notes 60,64,67,71 --hold 2 --seconds 3.5
bin/flagent_render dsp/moss-verb.jsfx --input pluck --seconds 8 --slider 4=1 --wav out.wav
```

| Option | Meaning |
|---|---|
| `--notes N,N,…`, `--velocity V`, `--hold S` | Play MIDI notes at t = 0, release after `hold` seconds |
| `--input none\|noise\|sine\|pluck`, `--input-seconds S` | Audio fed to the script (for effects) |
| `--seconds S`, `--rate HZ`, `--tempo BPM` | Render length, sample rate, host tempo (transport is playing) |
| `--slider I=V` | Set slider *I* (1-based) before rendering |
| `--wav PATH` | Also write a 32-bit float stereo WAV |

Output fields: `compiled`, `sliders`, `peak_db` (and per channel), `rms_db`, `tail_rms_db` (last 10%), `dc_offset`, `stereo_correlation`, `non_finite_samples`, `clipping`, `silent`, `log`. Exit code 2 means the script failed to load or compile.

### Script tests
`fl-studio-mcp/tests/test_jsfx_scripts.py` runs on every script in `dsp/`:
- **Lint:** fails if an identifier is spelled with two different cases.
- **Render:** instruments get a 5-note chord, effects a plucked input. The output must compile, have no NaN/inf, not clip, not be silent, and decay at least 20 dB after the input stops (catches runaway feedback).

The render tests are skipped if `bin/flagent_render` hasn't been built.
