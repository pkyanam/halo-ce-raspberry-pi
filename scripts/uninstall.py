#!/usr/bin/env python3
"""Remove installed application files and shortcuts; retain all game data."""
import json
import shutil
from pathlib import Path

prefix = Path(__file__).resolve().parent
marker = prefix / '.halo-ce-pi-install.json'
if not marker.is_file():
    raise SystemExit('Not an installed Halo CE Pi application directory.')
manifest = json.loads(marker.read_text())
shortcut = Path(manifest['shortcut'])
if shortcut.is_symlink() and shortcut.resolve() == prefix / 'play-halo-pi':
    shortcut.unlink()
if manifest.get('desktop'):
    desktop = Path(manifest['desktop'])
    if desktop.is_file() and str(prefix / 'play-halo-pi') in desktop.read_text():
        desktop.unlink()
for name in manifest['files']:
    path = prefix / name
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise SystemExit('Invalid installation manifest; stopping.')
    if path.is_file() or path.is_symlink():
        path.unlink()
# Ephemeral launcher files; maps/settings are links to the retained data folder.
profile = prefix / 'build/pi/play-performance'
if profile.is_symlink():
    profile.unlink()
elif profile.is_dir():
    shutil.rmtree(profile)
marker.unlink()
for directory in sorted(prefix.rglob('*'), key=lambda p: len(p.parts), reverse=True):
    if directory.is_dir() and not directory.is_symlink():
        try:
            directory.rmdir()
        except OSError:
            pass
try:
    prefix.rmdir()
except OSError:
    pass
print(f'Application removed. Your maps, settings and saves remain in {manifest["data"]}.')
