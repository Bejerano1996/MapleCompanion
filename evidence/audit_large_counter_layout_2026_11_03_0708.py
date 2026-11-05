from pathlib import Path
import sys,types,json,hashlib,tkinter as tk,gc
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import widgets
from training_ui import training_render_levelup
root=tk.Tk();root.withdraw();width=260;forecast={};text='';rows=[];previous_scale=widgets.text_scale
app=types.SimpleNamespace(state={'character_exp':{'level':99,'exp':1,'percent':99.99}},_lvl_spec=None,lvl_strip=tk.Frame(root),panel_width=lambda:width,training_forecast_now=lambda:forecast,training_forecast_text=lambda:text,companion_exp_details=lambda:None)
app.lvl_strip.pack(fill='x')
try:
 for scale in (1.,1.15,1.3):
  widgets.text_scale=scale
  for width in (260,280,340,520):
   for mode,text in enumerate(('≈94,821,615,480 Orange Mushroom → Lv 100','≈94,821,615,480 Very Long Monster Name With Several Words For Layout Boundary → Lv 100','Target unknown / mixed mobs · use Setup or show labels')):
    forecast=dict(available=mode!=2,kills=94821615480,probe_mode=mode);training_render_levelup(app);root.update_idletasks()
    counter=app.lvl_strip._training_nodes[1]
    assert counter.cget('text')==text
    assert counter.winfo_reqwidth()+12<=width,(scale,width,mode,counter.winfo_reqwidth())
    assert int(counter.cget('wraplength'))==max(200,width-35)
    rows.append(dict(scale=scale,panel_width=width,mode=mode,label_reqwidth=counter.winfo_reqwidth(),label_reqheight=counter.winfo_reqheight()))
 report=dict(ok=True,cases=len(rows),max_label_height=max(r['label_reqheight'] for r in rows),source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),cases_geometry=rows,scope='Own withdrawnTkproductionstrip requestedgeometry,hugecounter/longname/unknowntext,scales1/1.15/1.3,width260–520; not screenshot or fullapp/game')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='cases_geometry'}))
finally:widgets.text_scale=previous_scale;root.destroy()
