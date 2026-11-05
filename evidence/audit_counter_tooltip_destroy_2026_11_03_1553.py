from pathlib import Path
import sys,types,tkinter as tk,json,hashlib
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import training_ui,widgets
from companion_widgets import ui_walk_widgets
root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda k,e,t:errors.append(str(e))
a=types.SimpleNamespace(state={'character_exp':{'level':27,'exp':1000,'percent':1.5}},_lvl_spec=None,lvl_strip=tk.Frame(root,bg=widgets.C['card']),panel_width=lambda:340,training_forecast_now=lambda:{'available':True,'kills':5},training_forecast_text=lambda:'Approximate 5 Evil Eye remaining',companion_exp_details=lambda:None)
oldtip=None;oldjob=None;scheduled=0
for i in range(200):
 widgets.text_scale=(1.,1.15,1.3)[i%3]
 training_ui.training_render_levelup(a)
 if oldtip is not None:
  assert oldtip.job is None and oldtip.win is None
  assert oldjob not in root.tk.call('after','info')
 button=next(w for w in ui_walk_widgets(a.lvl_strip) if isinstance(w,tk.Button))
 tip=button._companion_tooltip
 tip._schedule();first=tip.job
 tip._schedule();assert first not in root.tk.call('after','info')
 oldtip=tip;oldjob=tip.job;scheduled+=2
 assert len(root.tk.call('after','info'))==1
root.update_idletasks();a.lvl_strip.destroy()
assert oldtip.job is None and not root.tk.call('after','info')
root.after(400,root.quit);root.mainloop()
assert not errors and not root.tk.call('after','info'),errors
report=dict(ok=True,font_rebuilds=200,tooltip_schedules=scheduled,pending_after_jobs=0,tk_errors=errors,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Actual compact counter+Tooltip delayed callbacks in isolated withdrawn Tk; schedule twice then destroy before350ms, drain400ms. No hover/game input/live application.')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));root.destroy()
