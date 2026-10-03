#!/usr/bin/env python3
"""Run an isolated, bounded real-game scene on the Pi's headless GPU."""
import argparse,json,os,re,subprocess,time,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-root',type=Path,default=Path(os.environ.get('HALO_DATA_ROOT',str(Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'halo-ce-raspberry-pi/game-data'))))
p.add_argument('--level',default='menu',choices=['menu','a10','a30','a50','b30','b40','c10','c20','c40','d20','d40'])
p.add_argument('--seconds',type=int,default=60)
p.add_argument('--name')
p.add_argument('--async',dest='pipeline',action='store_true')
p.add_argument('--audio',action='store_true')
p.add_argument('--audio-driver',default='dummy',help='SDL audio driver used with --audio: dummy, alsa, pulseaudio or auto')
p.add_argument('--screenshots',action='store_true')
p.add_argument('--input',dest='test_input',default='')
p.add_argument('--multiplayer-map',choices=['bloodgulch','beavercreek','carousel','chillout','damnation','hangemhigh','longest','prisoner','ratrace','wizard'],help='Load a multiplayer map locally with the Slayer game engine')
p.add_argument('--capture-every',type=int,default=300)
p.add_argument('--sample',type=int,default=0)
p.add_argument('--quality',choices=['original','performance'],default='original')
p.add_argument('--scale',type=float,default=1.0)
p.add_argument('--width',type=int,default=640)
a=p.parse_args()
name=a.name or f'{a.level}-{int(time.time())}'
if not re.fullmatch(r'[a-zA-Z0-9_-]+',name):p.error('name must contain letters, numbers, hyphens or underscores')
work=ROOT/'build/pi/tests'/name
work.mkdir(parents=True,exist_ok=False)
(work/'maps').symlink_to(a.data_root.resolve()/'maps',target_is_directory=True)
(work/'config.toml').write_text(f'[display]\nscreen_width = {a.width}\n[debug]\nsample_seconds = {a.sample}\n')
commands=[]
if a.level!='menu' and not a.multiplayer_map: commands.append(f'map_name levels\\{a.level}\\{a.level}')
if a.multiplayer_map:
 commands += ['game_variant slayer',f'map_name levels\\test\\{a.multiplayer_map}\\{a.multiplayer_map}']
if a.quality=='performance':
 commands += ['render_shadows false','rasterizer_environment_shadows false','rasterizer_detail_objects false','rasterizer_lens_flares false']
if commands:(work/'init.txt').write_text('\n'.join(commands)+'\n')
env=dict(os.environ,SDL_VIDEO_DRIVER='offscreen',EGL_PLATFORM='surfaceless',
 HALO_DATA_ROOT=str(work),HALO_EXIT_AFTER=str(a.seconds),HALO_NO_VSYNC='1',
 HALO_PI_BENCHMARK='async' if a.pipeline else '1',HALO_SAVE_ROOT=str(a.data_root.resolve()/'save'),HALO_PI_RENDER_SCALE=str(a.scale),HALO_INTERPOLATION='true',HALO_NO_AUDIO='0' if a.audio else '1')
env.setdefault('SDL_AUDIO_DEVICE_SAMPLE_FRAMES','2048')
if a.test_input: env['HALO_TEST_INPUT']=a.test_input
if a.audio:
 env.pop('HALO_NO_AUDIO',None)
 if a.audio_driver=='auto': env.pop('SDL_AUDIO_DRIVER',None)
 else: env['SDL_AUDIO_DRIVER']=a.audio_driver
if a.screenshots:
 (work/'screenshots').mkdir()
 env.update(HALO_SCREENSHOT_DIR=str(work/'screenshots'),HALO_SCREENSHOT_EVERY=str(a.capture_every))
def hardware():
 if not shutil.which("vcgencmd"): return {"temperature":"unavailable", "throttled":"unavailable"}
 return {key:subprocess.run(['vcgencmd',*command.split()],capture_output=True,text=True).stdout.strip() for key,command in [('temperature','measure_temp'),('throttled','get_throttled'),('cpu_clock','measure_clock arm'),('gpu_clock','measure_clock v3d')]}
before=hardware()
guest_hash=hashlib.sha256((ROOT/'build/pi/halo_guest.elf').read_bytes()).hexdigest()
settings={k:v for k,v in env.items() if k.startswith(('HALO_','SDL_')) or k=='mesa_glthread'}
if a.sample:
 shutil.copy2(ROOT/'build/pi/halo_guest.elf',work/'halo_guest.elf')
 shutil.copy2(ROOT/'build/pi/halo',work/'halo-host.elf')
start=time.monotonic()
with (work/'stdout.log').open('w') as log:
 try: status=subprocess.run([str(ROOT/'run-halo-pi')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=a.seconds+120).returncode
 except subprocess.TimeoutExpired:status=124
text=(work/'stdout.log').read_text(errors='replace')
samples=[]
for line in text.splitlines():
 if 'PI_BENCHMARK frames=' not in line: continue
 values=dict(re.findall(r'(frames|seconds|fps|worst_ms|p50_ms|p95_ms|p99_ms|cpu_ms|wait_ms|over_60_budget)=([0-9.]+)',line))
 samples.append({k:int(v) if k in ('frames','over_60_budget') else float(v) for k,v in values.items()})
result=dict(level=a.level,multiplayer_map=a.multiplayer_map,width=a.width,seconds=a.seconds,test_input=a.test_input,guest_sha256=guest_hash,settings=settings,pipelined=a.pipeline,audio=a.audio,scale=a.scale,quality=a.quality,screenshots=a.screenshots,exit_code=status,elapsed=time.monotonic()-start,samples=samples,hardware_before=before,hardware_after=hardware())
result['gl_errors']=len(re.findall(r'GL error [0-9a-f]+',text))
result['audio_underruns']=text.count('underrun occurred')
result['audio_invalid_samples']=sum(int(x) for x in re.findall(r'PI_AUDIO[^\n]*invalid=(\d+)',text))
if samples:
 result['average_fps']=sum(x['frames'] for x in samples)/sum(x['seconds'] for x in samples)
 result['minimum_interval_fps']=min(x['fps'] for x in samples)
(work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
print('Artifacts:',work,flush=True)
raise SystemExit(status if status>=0 else 1)
