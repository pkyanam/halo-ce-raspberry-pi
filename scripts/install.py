#!/usr/bin/env python3
"""Build and install the native Pi port without bundling game data."""
import argparse
import json
import os
import platform
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'halo-ce-raspberry-pi'
PACKAGES = '''git curl python3 ninja-build clang lld llvm gcc g++ cmake pkg-config
libegl1-mesa-dev libgles2-mesa-dev libdrm-dev libgbm-dev libasound2-dev libpulse-dev
libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxi-dev libxfixes-dev libxss-dev
libwayland-dev wayland-protocols libxkbcommon-dev libudev-dev libdbus-1-dev'''.split()
MARKER = '.halo-ce-pi-install.json'


def run(command, **kwargs):
    print('+ ' + shlex.join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), check=True, **kwargs)


def check_platform():
    if platform.machine() not in ('aarch64', 'arm64'):
        raise ValueError('Use a 64-bit ARM OS on the Raspberry Pi (aarch64), not a 32-bit OS.')
    release = {}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            release[k] = v.strip('"')
    if release.get('ID') not in ('debian', 'raspbian') or int(release.get('VERSION_ID', '0').split('.')[0]) < 13:
        raise ValueError('This installer supports Debian 13 / Raspberry Pi OS Trixie or newer. Other distributions are untested.')
    model = Path('/proc/device-tree/model')
    if not model.exists() or 'Raspberry Pi' not in model.read_text().rstrip('\0'):
        raise ValueError('Run the installer on the target Raspberry Pi.')


def check_elf(path):
    with path.open('rb') as file:
        header = file.read(20)
    if len(header) < 20 or header[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', header, 18)[0] != 183:
        raise ValueError(f'Expected a native little-endian ARM64 ELF file: {path}')


def import_maps(data, iso=None, maps=None, extractor=None):
    destination = data / 'maps'
    if destination.exists():
        if not (destination / 'ui.map').is_file():
            raise ValueError(f'{destination} exists but has no ui.map. Use a new --data-dir.')
        print(f'Keeping existing maps and saves in {data}.')
        return
    if iso:
        if not iso.is_file():
            raise ValueError(f'ISO not found: {iso}')
        run([extractor, iso, data])
    elif maps:
        if not (maps / 'ui.map').is_file():
            raise ValueError('--maps-dir must name the maps directory containing ui.map.')
        stage = data / 'maps.partial'
        if stage.exists():
            raise ValueError(f'Remove or inspect the interrupted import at {stage} before retrying.')
        stage.mkdir()
        try:
            for path in maps.glob('*.map'):
                shutil.copy2(path, stage / path.name)
            stage.rename(destination)
        except BaseException:
            shutil.rmtree(stage)
            raise
    else:
        print('Engine installed without game maps. Supply your own ISO or maps to play.')


def desktop_quote(path):
    value = str(path).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    return '"' + value + '"'


def install_runtime(prefix, data, bin_dir, desktop_dir, no_desktop=False):
    prefix.parent.mkdir(parents=True, exist_ok=True)
    if prefix.exists() and (not prefix.is_dir() or not (prefix / MARKER).is_file()):
        raise ValueError(f'Refusing to replace an unmanaged directory: {prefix}. Choose a new --prefix.')
    shortcut = bin_dir / 'halo-ce-pi'
    if (shortcut.exists() or shortcut.is_symlink()) and not (shortcut.is_symlink() and shortcut.resolve() == prefix / 'play-halo-pi'):
        raise ValueError(f'Refusing to replace another program at {shortcut}. Choose a new --bin-dir.')
    stage = Path(tempfile.mkdtemp(prefix='.halo-ce-stage-', dir=prefix.parent))
    backup = None
    files = []
    def copy(source, target):
        target = Path(target)
        (stage / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, stage / target)
        files.append(str(target))
    try:
        for name in ['halo', 'halo_guest.elf']:
            check_elf(ROOT / 'build/pi' / name)
            copy(ROOT / 'build/pi' / name, 'build/pi/' + name)
        library = ROOT / 'build/pi/sdl3-build/libSDL3.so'
        check_elf(library)
        copy(library, 'build/pi/libSDL3.so.0')
        copy(ROOT / 'build/pi/extract-maps', 'tools/extract-maps')
        for name in ['run-halo-pi', 'play-halo-pi', 'benchmark-halo-pi']:
            copy(ROOT / name, name)
        copy(ROOT / 'scripts/uninstall.py', 'uninstall.py')
        copy(ROOT / 'port/android/art/android-icon.png', 'icons/halo.png')
        copy(ROOT / 'LICENSE.md', 'LICENSE.md')
        copy(ROOT / 'README.md', 'README.md')
        for path in sorted((ROOT / 'port/third_party').rglob('*')):
            if path.is_file() and any(word in path.name.upper() for word in ['LICENSE', 'COPYRIGHT']):
                copy(path, Path('licenses') / path.relative_to(ROOT / 'port'))
        for path in (ROOT / 'port/assets/fonts').glob('*.txt'):
            copy(path, Path('licenses/fonts') / path.name)
        for source, target in [('build/pi/third_party/SDL3/LICENSE.txt', 'licenses/SDL3-LICENSE.txt'),
                               ('build/pi/third_party/musl-1.2.5/COPYRIGHT', 'licenses/musl-COPYRIGHT')]:
            if (ROOT / source).is_file():
                copy(ROOT / source, target)
        (stage / 'data-root').write_text(str(data) + '\n')
        files.append('data-root')
        shortcut = bin_dir / 'halo-ce-pi'
        desktop = None if no_desktop else desktop_dir / 'halo-ce-raspberry-pi.desktop'
        manifest = dict(files=files, data=str(data), shortcut=str(shortcut), desktop=str(desktop) if desktop else None)
        (stage / MARKER).write_text(json.dumps(manifest, indent=2) + '\n')
        if prefix.exists():
            backup = Path(tempfile.mkdtemp(prefix='.halo-ce-backup-', dir=prefix.parent))
            backup.rmdir()
            prefix.rename(backup)
        try:
            stage.rename(prefix)
        except BaseException:
            if backup:
                backup.rename(prefix)
            raise
        if backup:
            shutil.rmtree(backup)
        bin_dir.mkdir(parents=True, exist_ok=True)
        if shortcut.is_symlink() and shortcut.resolve() == prefix / 'play-halo-pi':
            shortcut.unlink()
        elif shortcut.exists() or shortcut.is_symlink():
            raise ValueError(f'App installed, but shortcut already belongs to another program: {shortcut}')
        shortcut.symlink_to(prefix / 'play-halo-pi')
        if desktop:
            desktop_dir.mkdir(parents=True, exist_ok=True)
            desktop.write_text('[Desktop Entry]\nType=Application\nName=Halo: Combat Evolved (Raspberry Pi)\n'
                               'Comment=Native ARM Halo CE port\n'
                               f'Exec={desktop_quote(prefix / "play-halo-pi")}\n'
                               f'Icon={prefix / "icons/halo.png"}\nTerminal=true\nCategories=Game;ActionGame;\n')
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, default=BASE / 'app', help='Application directory')
    parser.add_argument('--data-dir', type=Path, help='Maps/settings/saves directory (preserved on uninstall)')
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument('--iso', type=Path, help='Your Xbox Halo CE disc image / xiso')
    inputs.add_argument('--maps-dir', type=Path, help='Your already-extracted maps directory')
    parser.add_argument('--jobs', type=int, default=2, choices=range(1, 9), help='Build jobs (default: 2)')
    parser.add_argument('--skip-deps', action='store_true', help='Skip apt; dependencies must already be installed')
    parser.add_argument('--skip-build', action='store_true', help='Package an existing build/pi build')
    parser.add_argument('--data-only', action='store_true', help='Import maps into an existing installation')
    parser.add_argument('--dry-run', action='store_true', help='Print plan without changing anything')
    parser.add_argument('--bin-dir', type=Path, default=Path.home() / '.local/bin')
    parser.add_argument('--desktop-dir', type=Path, default=Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'applications')
    parser.add_argument('--no-desktop', action='store_true', help='Omit the Games menu shortcut')
    args = parser.parse_args()
    prefix = args.prefix.expanduser().resolve()
    existing = prefix / 'data-root'
    data = (args.data_dir or (Path(existing.read_text().strip()) if existing.exists() else BASE / 'game-data')).expanduser().resolve()
    for path in [prefix, data, args.bin_dir, args.desktop_dir]:
        if '\n' in str(path) or '\r' in str(path):
            raise ValueError('Installation paths cannot contain line breaks.')
    if data == prefix or prefix in data.parents or data in prefix.parents:
        raise ValueError('--prefix and --data-dir must be separate, non-nested directories.')
    print(f'Application: {prefix}\nGame data:   {data}\nBuild jobs:  {args.jobs}', flush=True)
    if args.dry_run:
        print('Plan: verify 64-bit Pi / Debian 13+, install missing apt dependencies, build native engine,')
        print('import supplied maps (if any), install user-local runtime, command and Games shortcut.')
        print('No changes made. No ISO or game maps are downloaded.')
        return
    check_platform()
    if os.geteuid() == 0:
        raise ValueError('Run as your normal desktop user, without sudo. Only apt uses sudo.')
    if args.iso and not args.iso.expanduser().is_file():
        raise ValueError(f'ISO not found: {args.iso}')
    if args.maps_dir and not (args.maps_dir.expanduser() / 'ui.map').is_file():
        raise ValueError('The --maps-dir directory must contain ui.map.')
    if args.data_only:
        extractor = prefix / 'tools/extract-maps'
        if not (prefix / MARKER).is_file() or not extractor.is_file():
            raise ValueError('--data-only requires an existing installation at --prefix.')
    else:
        if prefix.exists() and not (prefix / MARKER).is_file():
            raise ValueError(f'Application path is not managed by this installer: {prefix}')
        if not args.skip_deps:
            missing = []
            for package in PACKAGES:
                result = subprocess.run(['dpkg-query', '-W', '-f=${Status}', package], capture_output=True, text=True)
                if result.returncode or result.stdout.strip() != 'install ok installed':
                    missing.append(package)
            if missing:
                run(['sudo', 'apt-get', 'update'])
                run(['sudo', 'apt-get', 'install', '-y', *missing])
        if not args.skip_build:
            for tool in ['clang', 'ld.lld', 'llvm-objcopy', 'gcc', 'cmake', 'ninja', 'git', 'curl']:
                if not shutil.which(tool):
                    raise ValueError(f'Missing build tool {tool}; rerun without --skip-deps.')
            run([sys.executable, 'configure_pi.py', '--optimization', 'O3'], cwd=ROOT)
            run(['ninja', '-f', 'build-pi.ninja', '-j', str(args.jobs), 'pi'], cwd=ROOT)
        (ROOT / 'build/pi').mkdir(parents=True, exist_ok=True)
        extractor = ROOT / 'build/pi/extract-maps'
        run(['cc', '-O2', '-Iport/linux/src', 'port/pi/extract_maps.c', '-o', extractor], cwd=ROOT)
    data.mkdir(parents=True, exist_ok=True)
    import_maps(data, args.iso.expanduser().resolve() if args.iso else None,
                args.maps_dir.expanduser().resolve() if args.maps_dir else None, extractor)
    if args.data_only:
        existing.write_text(str(data) + '\n')
        manifest = json.loads((prefix / MARKER).read_text())
        manifest['data'] = str(data)
        (prefix / MARKER).write_text(json.dumps(manifest, indent=2) + '\n')
    else:
        install_runtime(prefix, data, args.bin_dir.expanduser().resolve(), args.desktop_dir.expanduser().resolve(), args.no_desktop)
    print('\nInstalled. Launch from the Games menu or run:')
    print(shlex.join([str(args.bin_dir.expanduser().resolve() / 'halo-ce-pi'), '--performance']))
    print('Use without --performance for normal graphics. Game data and saves are preserved on reinstall/uninstall.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Installation failed: {error}', file=sys.stderr)
        sys.exit(1)
