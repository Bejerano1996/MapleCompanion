from pathlib import Path
import sys,types,tkinter as tk,time,json,statistics,hashlib,random,gc
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
from training_ui import training_render_levelup
root=tk.Tk();root.withdraw();width=340;durations=[];rng=random.Random(1107)
try:
 a=types.SimpleNamespace(state={'character_exp':{'level':27,'exp':1000,'percent':1.5}},_lvl_spec=None,lvl_strip=tk.Frame(root),panel_width=lambda:width,training_forecast_now=lambda:{'available':True,'kills':5},training_forecast_text=lambda:'Approximate remaining kills with a long monster name',companion_exp_details=lambda:None)
 training_render_levelup(a);root.update_idletasks();gc.collect()
 children=tuple(str(w) for w in a.lvl_strip.winfo_children());fonts=len(root.tk.call('font','names'));images=len(root.tk.call('image','names'))
 for index in range(1500):
  width=rng.randint(260,700);a.state['character_exp']['exp']=1000+index
  start=time.perf_counter();training_render_levelup(a);durations.append(time.perf_counter()-start)
  assert int(a.lvl_strip._training_nodes[1].cget('wraplength'))==max(200,width-35)
  assert children==tuple(str(w) for w in a.lvl_strip.winfo_children())
  if index%50==0:root.update_idletasks()
 gc.collect();root.update_idletasks()
 assert len(root.tk.call('font','names'))==fonts
 assert len(root.tk.call('image','names'))==images
 report=dict(ok=True,updates=1500,median_render_ms=round(statistics.median(durations)*1000,3),p99_render_ms=round(sorted(durations)[int(len(durations)*.99)]*1000,3),fonts=fonts,images=images,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Isolated native Tk strip with simulated width/EXP updates; render-call timings exclude full application and OCR,not live gameplay')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:root.destroy()
