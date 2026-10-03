#!/usr/bin/env python3
"""Summarize saved Pi runs without conflating loading, lobby and gameplay."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['run', 'scene', 'exit_code', 'scene_valid', 'seconds', 'scale', 'quality',
          'audio', 'screenshots', 'pipeline', 'average_fps', 'last_six_intervals_fps',
          'minimum_interval_fps', 'gl_debug', 'gl_errors', 'audio_underruns',
          'audio_invalid_samples', 'temperature_after', 'throttled_after', 'notes']
rows = []
for path in sorted((ROOT / 'build/pi/tests').glob('*/result.json')):
    r = json.loads(path.read_text())
    log = (path.parent / 'stdout.log').read_text(errors='replace')
    samples = r.get('samples', [])[-6:]
    duration = sum(x['seconds'] for x in samples)
    late = sum(x['frames'] for x in samples) / duration if duration else 0
    rows.append(dict(zip(FIELDS, [path.parent.name, r.get('multiplayer_map') or r['level'],
        r['exit_code'], r.get('scene_valid', True), r['seconds'], r.get('scale', 1),
        r.get('quality', 'original'), r.get('audio', False), r.get('screenshots', False),
        r.get('pipelined', False), round(r.get('average_fps', 0), 2), round(late, 2),
        r.get('minimum_interval_fps', 0),
        r.get('settings', {}).get('HALO_GL_DEBUG') in ('1', 'true'),
        len(re.findall(r'GL error [0-9a-f]+', log)), log.count('underrun occurred'),
        sum(int(x) for x in re.findall(r'PI_AUDIO[^\n]*invalid=(\d+)', log)),
        r['hardware_after']['temperature'],
        r['hardware_after']['throttled'], r.get('validation_notes', '')])))
output = ROOT / 'build/pi/results.csv'
with output.open('w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
print(output)
for r in rows:
    if r['run'].startswith('campaign-o3-') or r['run'].endswith('-o3'):
        print(f"{r['run']:<30} exit={r['exit_code']} valid={r['scene_valid']} "
              f"average={r['average_fps']:.1f} late={r['last_six_intervals_fps']:.1f}")
