from pathlib import Path
import sys,types,json,copy,gc,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from companion_tools import utility_render_compare
from companion_widgets import ui_walk_widgets
root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda kind,error,tb:errors.append(str(error))
good=dict(finished_at=1,running_since=None,map_id='A',map_name='Valid A',elapsed=100,mesos=10,cost=0,exp=20,kills=1,money_elapsed_anchor=50)
history=[good,dict(good,map_id='B',map_name='Valid B',exp=50)]
for mode,key in [('wallet','wallet_elapsed_anchor'),('notices','money_elapsed_anchor')]:
 for value in ('bad',True,-1,101):history.append(dict(good,money_mode=mode,**{key:value}))
before=copy.deepcopy(history);app=types.SimpleNamespace(state={'utility_session_history':history},db=types.SimpleNamespace(maps={}),start_route=lambda *a:None)
frame=tk.Frame(root);frame.pack();utility_render_compare(app,frame);root.update();checks=[]
assert app._utility_last_comparison['excluded']['invalid']==8
assert len(app._utility_last_comparison['maps'])==2
checks.append('Both valid maps remain visible beside eight invalid rows')
for i in range(60):
 title=('EXP/h','Net mesos/h','Kills/h','Refresh')[i%4]
 next(w for w in ui_walk_widgets(frame) if isinstance(w,tk.Button) and w.cget('text')==title).invoke();root.update()
 assert app._utility_last_comparison['excluded']['invalid']==8
 assert sum(r['sessions'] for r in app._utility_last_comparison['maps'])==2
 assert all(r['net_hour']==720 for r in app._utility_last_comparison['maps'])
checks.append('Sixty native sort and refresh actions preserve exact valid rates')
texts=[w.cget('text') for w in ui_walk_widgets(frame) if isinstance(w,tk.Label)]
assert any('Excluded records: 8' in text for text in texts);checks.append('Excluded count is shown')
assert history==before;checks.append('Saved-history objects are unchanged')
assert not errors;checks.append('No Tk callback errors')
report=dict(ok=True,checks=checks,refreshes=60,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path(__file__).resolve().parents[1].glob('*.py')))).hexdigest(),scope='Isolated withdrawn own Tk comparison screen with synthetic history, no actual app save/game/OCR/network')
print(json.dumps(report));root.destroy()
