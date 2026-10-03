# Pi developer notes

For installation and play, start with the [project README](../../README.md).

## Build

```bash
python3 configure_pi.py --optimization O3
ninja -f build-pi.ninja -j2 pi
```

O3 applies to game sources; platform/musl use O2. Cortex-A72, release assertions,
no fused floating-point contractions, no PGO. O2 is available for comparisons.
SDL3 3.4.16 and musl 1.2.5 are fetched during configuration. The original
`ninja linux` target is x86; use the Pi graph.

The guest uses clang's arm64_32 Apple target for native ARM64 instructions
with 32-bit pointers. Upstream tools convert its assembly to ELF. Musl supplies
the guest libc; a glibc host bridges SDL, GLES and syscalls. Internal ABI/rule
names retain some Android-port names; Android is not required.

Changes include portable Linux paths, environment forwarding, stderr logging,
GLES lookup, guest stat conversion, persistent coherent fenced stream buffers,
shadow-mip copy caching, render scaling and the first-present FBO fix.
`HALO_PI_PERSISTENT=0` and `HALO_PI_MIP_CACHE=0` disable optimizations for comparison.
An origin-relative SDL runtime path allows relocation of installed files together.

## Hardware tests

Set `HALO_DATA_ROOT` to your game-data directory or use the installer default.
Individual runs also accept `--data-root /path/to/game-data`.

```bash
python3 tools/pi_gpu_probe.py
python3 tools/pi_benchmark.py --level menu --seconds 60 --async
python3 tools/pi_benchmark.py --level a30 --seconds 90 --async
python3 tools/pi_benchmark.py --level a30 --seconds 90 --async --scale 0.5 --quality performance
python3 tools/pi_benchmark.py --multiplayer-map bloodgulch --input bot:1 --seconds 180 --async
python3 tools/pi_campaign_suite.py --seconds 90 --prefix campaign-test
python3 tools/pi_results.py
```

Runs get unique folders under `build/pi/tests/`: settings, commands, logs,
optional screenshots and JSON stats. Saves/map caches are shared with the
chosen data directory; use a copy if you have valuable campaign progress.
`--async` keeps CPU/GPU overlap and drains before exit; without it, glFinish
runs each frame. Intervals include frame percentiles, submission/wait time,
temperature and throttling. Startup/shader compilation are included.

`--screenshots --capture-every 1000` adds visual checks with capture overhead.
`--input bot:1` exercises movement, looking, firing, jumping and grenades.
`--audio` uses dummy audio; `--audio --audio-driver auto` tests normal selection.
`alsa` and `pulseaudio` select explicit backends.

`HALO_GL_DEBUG=1` enables guest checks and KHR_debug driver messages.
`HALO_PI_GL_PROFILE=1` times selected GL calls. `--sample 1` captures thread
stacks and matching binaries. `HALO_PI_AUDIO_STATS=1` reports signal/invalid
samples; `HALO_PI_AUDIO_CAPTURE=/path/audio.f32` captures float PCM.
`build/pi/results.csv` summarizes runs. See [measurements](../../docs/PERFORMANCE.md).

## Extract manually

```bash
cc -O2 -Iport/linux/src port/pi/extract_maps.c -o build/pi/extract-maps
build/pi/extract-maps '/path/to/Halo.iso' '/path/to/new-game-data'
```

Extraction writes `maps.partial`, then renames after completion. Choose a new
folder if maps already exist. Format handling follows upstream xiso.c; notices
are retained in source and `port/third_party/extract-xiso/LICENSE.TXT`.
