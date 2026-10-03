# Halo: Combat Evolved on Raspberry Pi

## Install

Use **64-bit Raspberry Pi OS Trixie / Debian 13**. Tested on a **Raspberry Pi 4
Model B with 8 GB RAM**. Allow several GB of free space and use suitable cooling.

```bash
git clone https://github.com/pkyanam/halo-ce-raspberry-pi.git
cd halo-ce-raspberry-pi
./install.sh --iso "/path/to/Halo - Combat Evolved.iso"
```

Run as your normal user. The installer asks for administrator access only to
install missing system packages, builds the native engine, extracts your maps,
and adds a **Games-menu shortcut** and launch command. The first build takes
a while; two build jobs are used by default.

**Provide your own Xbox Halo CE ISO/xiso or extracted maps.** No ISO, maps,
music, saves or original game data are included or downloaded. The USA Rev 1
xiso was tested; images must contain the Xbox XDVDFS filesystem.

Already have maps, or want to add a game after installing the engine?

```bash
./install.sh --maps-dir "/path/to/maps"

# Alternatively: install now, import your disc later.
./install.sh
./install.sh --data-only --iso "/path/to/Halo.iso"
```

## Play

Launch **Halo: Combat Evolved (Raspberry Pi)** from Games, or run:

```bash
~/.local/bin/halo-ce-pi --performance
```

The performance profile renders **320×240, 4:3**, disabling dynamic shadows,
decorative detail objects and lens flares. Omit `--performance` for normal
graphics. Both profiles use the same settings and saves.

Desktop and remote-desktop sessions work. From SSH with HDMI connected, the
launcher discovers your existing Wayland desktop; without a desktop it uses
KMSDRM. Physical HDMI presentation was not tested during development. Remote
desktop may select a different graphics driver and have different performance.

Keyboard/mouse: WASD move, mouse aim, left click fire, Space jump, E/R
action/reload, F melee, G/right click grenade, Tab change weapon, Q flashlight,
Escape pause. Gamepads are supported.

## Performance

This is a **native ARM64 port**, with the engine's required 32-bit pointers
inside an ARM64 host. It uses SDL3 and Mesa GLES, without x86 emulation or an
Android installation. Other Pi models and OS versions are untested.

**Sustained 60 fps across the campaign has not been achieved.** Menu and
cutscene frame rates do not establish campaign performance.

| Headless Pi 4 / 8 GB test | Average fps |
| --- | ---: |
| Menu with audio | About 100 |
| Ten campaign openings, 640×480 / original effects | 21–52 |
| Five-minute scripted campaign combat, performance profile | About 37 |
| Three-minute local Blood Gulch / one player, performance profile | About 70 |

All ten campaign openings loaded; combat, HUD rendering, audio mixing, local
Slayer, offscreen and Wayland hardware rendering were tested. See
[test details](docs/PERFORMANCE.md) and [developer notes](port/pi/README.md).
Cooling helps avoid clock reductions, but an unthrottled campaign test still
averaged about 22 fps. Bink movies are skipped upstream; in-engine cutscenes work.

## Multiplayer

The upstream **128-player / 128-machine multiplayer limit is retained**.
This package does not reduce it. A populated 128-player session has **not**
been tested on the Pi. The one-player benchmark does not predict its performance.
LAN/system-link functionality remains available. Internet invites are opt-in:

```bash
HALO_NET_ONLINE=true ~/.local/bin/halo-ce-pi --performance
```

See [upstream multiplayer documentation](port/linux/README.md) and
[network implementation notes](port/linux/NETCODE.md). Upstream automatic binary
updates are disabled for this Pi build; update through this repository.

## Files, updates and uninstall

| Item | Default location |
| --- | --- |
| Application | `~/.local/share/halo-ce-raspberry-pi/app/` |
| Maps | `~/.local/share/halo-ce-raspberry-pi/game-data/maps/` |
| Saves | `~/.local/share/halo-ce-raspberry-pi/game-data/save/` |
| Settings | `~/.local/share/halo-ce-raspberry-pi/game-data/config.toml` |
| Command | `~/.local/bin/halo-ce-pi` |

`XDG_DATA_HOME` is honored. Reinstalling preserves maps, settings and saves.
Update from your source checkout:

```bash
git pull --ff-only
./install.sh
```

Remove the application and shortcuts **while keeping game data**:

```bash
python3 ~/.local/share/halo-ce-raspberry-pi/app/uninstall.py
```

Use `./install.sh --help` for options. Common examples:

```bash
./install.sh --dry-run
./install.sh --data-dir "$HOME/Games/HaloData" --iso "/path/to/Halo.iso"
./install.sh --skip-deps --jobs 2
```

Run without `--skip-deps` for normal setup. `--prefix` chooses an application
directory separate from game data. To replace maps with a different disc image,
choose a new `--data-dir`; existing maps are deliberately kept. For a custom
application prefix, run that prefix's `uninstall.py`.

## Credits

Based on [cybersecurity/halo-ce-universal](https://github.com/cybersecurity/halo-ce-universal)
at `0182da817285b67eee8264663ca79f7c32d66b5e`, which builds on
[bnunu/halo-1](https://github.com/bnunu/halo-1) and
[punpckhdq/halo](https://github.com/punpckhdq/halo). The Pi runtime adapts the
upstream Android ILP32 guest and Linux renderer.

Upstream source history, [original README](README.upstream.md),
[CC0 license](LICENSE.md) and third-party notices are retained. Runtime license
notices are installed too. Halo and its original assets belong to their
respective owners; this project does not distribute that game data.
