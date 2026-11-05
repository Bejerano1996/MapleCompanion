from pathlib import Path
import sys,tempfile,json,hashlib,copy,tkinter as tk
from unittest.mock import patch
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import app
app.App.run_bg=lambda *args,**kwargs:None;app.App.sync_from_game=lambda *args,**kwargs:None;app.App.prefetch=lambda *args,**kwargs:None
class NoHotkey:
 def __init__(self,*args,**kwargs):pass
 def start(self):pass
app.HotkeyThread=NoHotkey
cases=0;errors=[]
with tempfile.TemporaryDirectory(prefix='session-save-reload-',dir=rootpath.parent) as folder:
 app.STATE_FILE=str(Path(folder)/'state.json')
 for exp in (-1000,-1,0,1,500):
  for running in (False,True):
   Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'active':[]}))
   root=tk.Tk();root.withdraw();root.report_callback_exception=lambda k,e,t:errors.append(str(e));a=app.App(root);root.withdraw()
   current=dict(id=f'audit-{cases}',started_at=800.,elapsed=10.,running_since=900. if running else None,exp=exp,party_exp=17,kills=7,mesos=80,cost=90,reading_gaps=2,exp_is_net=True,exp_source='EXP bar · net',money_elapsed_anchor=3.)
   a.state['utility_session']=current;a.state['utility_session_history']=[dict(current,running_since=None)]
   prior=copy.deepcopy(current);history=copy.deepcopy(a.state['utility_session_history'])
   with patch('time.time',return_value=1000.):a.save_state()
   assert a.state['utility_session'] is current and current==prior
   saved=json.loads(Path(app.STATE_FILE).read_text());stored=saved['utility_session']
   assert stored['running_since'] is None and stored['elapsed']==(110. if running else 10.)
   for key in ('id','exp','party_exp','kills','mesos','cost','reading_gaps','exp_is_net','exp_source','money_elapsed_anchor'):assert stored[key]==prior[key],key
   root.destroy()
   root=tk.Tk();root.withdraw();root.report_callback_exception=lambda k,e,t:errors.append(str(e))
   with patch('time.time',return_value=9000.):a=app.App(root)
   root.withdraw();assert a.state['utility_session']==stored
   assert a.state['utility_session_history']==history
   root.update_idletasks();root.destroy();cases+=1
assert not errors,errors
report=dict(ok=True,cases=cases,negative_net_values=[-1000,-1],running_snapshot_elapsed_preserved=True,offline_gap_not_counted=True,tk_errors=errors,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Actual native CompanionApp save_state and startup reload in temporary state file only; paused/running snapshots, synthetic session counters/time, no game/network/capture/hotkeys')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
