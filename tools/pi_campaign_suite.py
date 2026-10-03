#!/usr/bin/env python3
"""Sequential campaign smoke and throughput tests, keeping the Pi GPU isolated."""
import argparse,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--seconds',type=int,default=75)
p.add_argument('--scale',type=float,default=1)
p.add_argument('--quality',choices=['original','performance'],default='original')
p.add_argument('--prefix',default='campaign-o3')
p.add_argument('--levels',nargs='+',default=['a10','a30','a50','b30','b40','c10','c20','c40','d20','d40'])
a=p.parse_args()
results=[]
for level in a.levels:
 name=f'{a.prefix}-{level}'
 print(f'Starting {level}: {a.seconds}s, scale {a.scale}, {a.quality}',flush=True)
 log=ROOT/'build/pi'/f'{name}.runner.log'
 with log.open('w') as out:
  status=subprocess.run([sys.executable,str(ROOT/'tools/pi_benchmark.py'),'--level',level,'--seconds',str(a.seconds),'--name',name,'--scale',str(a.scale),'--quality',a.quality,'--async'],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT).returncode
 result_file=ROOT/'build/pi/tests'/name/'result.json'
 r=json.loads(result_file.read_text()) if result_file.exists() else dict(level=level,exit_code=status)
 results.append(r)
 print(f"Finished {level}: exit {status}, average {r.get('average_fps',0):.1f} FPS, minimum interval {r.get('minimum_interval_fps',0):.1f} FPS",flush=True)
 (ROOT/'build/pi'/f'{a.prefix}-suite.json').write_text(json.dumps(results,indent=2)+'\n')
 if status:print(f'Check {log}',flush=True)
print('Campaign suite finished',flush=True)
raise SystemExit(any(r['exit_code'] for r in results))
