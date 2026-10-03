# Pi 4 validation

Measured on 2026-10-02: Pi 4 Model B / 8 GB, 64-bit Debian 13, clang 19.1.7,
Mesa 26.2.2, hardware V3D 4.2 and OpenGL ES 3.1. Game sources used O3 / Cortex-A72.

Ten 90-second campaign-opening tests at 640×480 / original effects exited
normally. These are opening scenes, not whole-level completion tests.

| Level | Whole-run average fps | Last six measured intervals, fps |
| --- | ---: | ---: |
| a10 | 51.8 | 52.0 |
| a30 | 21.4 | 19.1 |
| a50 | 34.7 | 42.2 |
| b30 | 21.4 | 18.1 |
| b40 | 40.9 | 33.5 |
| c10 | 31.2 | 39.2 |
| c20 | 26.8 | 25.2 |
| c40 | 32.5 | 36.7 |
| d20 | 26.8 | 21.5 |
| d40 | 46.0 | 35.4 |

The reduced-effects 320×240 profile improved some scenes substantially, but
has not sustained 60 fps across the campaign. Five-minute scripted a30 combat
averaged 37.2 fps; three-minute one-player local Blood Gulch averaged 69.8 fps.
Neither predicts a populated multiplayer session. A 160×120 a30 experiment
still averaged only 39.0 fps.

Hardware EGL offscreen tests preserved CPU/GPU overlap, used the renderer's
fenced stream ring and drained the GPU before exit. Five-second intervals
include startup, loading and shader compilation; some cold stalls lasted several
seconds. Screenshot and GL diagnostics add overhead; clean comparisons omit captures.

Menu/combat/HUD screenshots were inspected. Scripted input exercised movement,
looking, firing, jumping and grenade controls. Actual firing and incoming damage
were visible. Combat GL checks and finite/nonzero stereo audio mixing passed.
Direct ALSA initially underrran with a 1024-frame buffer; requesting 2048 frames
eliminated reported underruns in a repeated 45-second test. Automatic PulseAudio
selection passed too. Actual audible quality was unverified.

Wayland exposed an upstream first-present FBO binding error, fixed by creating
the source framebuffer before binding the window as the draw target. The final
binary was rechecked on Wayland/offscreen with no GL or driver errors. Bulk
throughput measurements precede that presentation fix; its steady-state path is unchanged.

Temperatures reached roughly 82–84°C and sometimes reduced GPU clocks from
500 to 333 MHz. A later a30 run at 78.4°C / 1.8 GHz CPU / 500 MHz GPU still
averaged about 22 fps. No overclock, voltage/boot changes or service shutdowns.

HDMI connectors were disconnected; physical HDMI pacing and physical controls
were unverified. The owner subsequently confirmed running over remote desktop.
An initial system-link test stayed in the lobby because that mode needs two
machines; its lobby FPS was excluded. An externally interrupted capture was repeated.

Harnesses are included; game maps, captures, private logs and saves are excluded.
