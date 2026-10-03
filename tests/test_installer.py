import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'scripts/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='halo test ')
        self.base = Path(self.temp.name)
        self.original_root = installer.ROOT

    def tearDown(self):
        installer.ROOT = self.original_root
        self.temp.cleanup()

    def test_map_import_preserves_existing_maps_and_saves(self):
        data = self.base / 'game data'
        (data / 'maps').mkdir(parents=True)
        (data / 'save').mkdir()
        (data / 'maps/ui.map').write_bytes(b'original')
        (data / 'save/progress').write_bytes(b'valuable save')
        installer.import_maps(data, iso=self.base / 'missing.iso')
        self.assertEqual((data / 'maps/ui.map').read_bytes(), b'original')
        self.assertEqual((data / 'save/progress').read_bytes(), b'valuable save')

    def test_map_import_only_copies_maps_and_renames_complete_folder(self):
        data = self.base / 'data'
        data.mkdir()
        maps = self.base / 'original maps'
        maps.mkdir()
        (maps / 'ui.map').write_bytes(b'ui')
        (maps / 'a10.map').write_bytes(b'level')
        (maps / 'unrelated.txt').write_text('keep out')
        installer.import_maps(data, maps=maps)
        self.assertEqual(sorted(p.name for p in (data / 'maps').iterdir()), ['a10.map', 'ui.map'])
        self.assertFalse((data / 'maps.partial').exists())

    def test_invalid_map_directory_does_not_publish_maps(self):
        data = self.base / 'data'
        data.mkdir()
        with self.assertRaises(ValueError):
            installer.import_maps(data, maps=self.base)
        self.assertFalse((data / 'maps').exists())

    def test_rejects_x86_binary(self):
        binary = self.base / 'wrong'
        header = bytearray(20)
        header[:6] = b'\x7fELF\x02\x01'
        struct.pack_into('<H', header, 18, 62)
        binary.write_bytes(header)
        with self.assertRaises(ValueError):
            installer.check_elf(binary)

    def fixture(self):
        source = self.base / 'source'
        source.mkdir()
        for name in ['build/pi/halo', 'build/pi/halo_guest.elf', 'build/pi/sdl3-build/libSDL3.so']:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            header = bytearray(20)
            header[:6] = b'\x7fELF\x02\x01'
            struct.pack_into('<H', header, 18, 183)
            path.write_bytes(header)
        for name in ['build/pi/extract-maps', 'run-halo-pi', 'play-halo-pi', 'benchmark-halo-pi',
                     'port/android/art/android-icon.png', 'LICENSE.md', 'README.md']:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture')
        (source / 'scripts').mkdir()
        (source / 'scripts/uninstall.py').write_text((ROOT / 'scripts/uninstall.py').read_text())
        installer.ROOT = source
        return source

    def test_install_reinstall_uninstall_preserves_data_with_space_paths(self):
        self.fixture()
        prefix = self.base / 'installed app'
        data = self.base / 'my game data'
        data.mkdir()
        save = data / 'save.bin'
        save.write_bytes(b'valuable progress')
        bin_dir, desktop = self.base / 'commands', self.base / 'desktop entries'
        installer.install_runtime(prefix, data, bin_dir, desktop)
        self.assertEqual((bin_dir / 'halo-ce-pi').resolve(), prefix / 'play-halo-pi')
        self.assertTrue((prefix / installer.MARKER).is_file())
        installer.install_runtime(prefix, data, bin_dir, desktop)
        subprocess.run([sys.executable, str(prefix / 'uninstall.py')], check=True, capture_output=True)
        self.assertEqual(save.read_bytes(), b'valuable progress')
        self.assertFalse(prefix.exists())
        self.assertFalse((bin_dir / 'halo-ce-pi').is_symlink())
        self.assertFalse((desktop / 'halo-ce-raspberry-pi.desktop').exists())

    def test_refuses_to_replace_unmanaged_app_directory(self):
        self.fixture()
        prefix = self.base / 'existing unrelated application'
        prefix.mkdir()
        sentinel = prefix / 'important'
        sentinel.write_text('do not overwrite')
        with self.assertRaises(ValueError):
            installer.install_runtime(prefix, self.base / 'data', self.base / 'bin', self.base / 'desktop')
        self.assertEqual(sentinel.read_text(), 'do not overwrite')

    def test_bad_build_keeps_previous_install(self):
        source = self.fixture()
        prefix = self.base / 'app'
        prefix.mkdir()
        (prefix / installer.MARKER).write_text('{}')
        (prefix / 'old executable').write_text('working')
        (source / 'build/pi/halo_guest.elf').write_bytes(b'broken build')
        with self.assertRaises(ValueError):
            installer.install_runtime(prefix, self.base / 'data', self.base / 'bin', self.base / 'desktop')
        self.assertEqual((prefix / 'old executable').read_text(), 'working')

    def test_foreign_command_does_not_publish_app(self):
        self.fixture()
        prefix, bin_dir = self.base / 'app', self.base / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'halo-ce-pi').write_text('another program')
        with self.assertRaises(ValueError):
            installer.install_runtime(prefix, self.base / 'data', bin_dir, self.base / 'desktop')
        self.assertFalse(prefix.exists())
        self.assertEqual((bin_dir / 'halo-ce-pi').read_text(), 'another program')

    def test_dry_run_makes_no_files(self):
        prefix, data = self.base / 'app', self.base / 'data'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install.py'), '--dry-run',
                                 '--prefix', str(prefix), '--data-dir', str(data)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No changes made', result.stdout)
        self.assertFalse(prefix.exists())
        self.assertFalse(data.exists())


if __name__ == '__main__':
    unittest.main()
