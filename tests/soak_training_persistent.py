"""Long-lived, isolated Tk session fed a synthetic game stream. No screen capture or input."""
from pathlib import Path
import sys,os,json,time,tempfile,argparse,gc
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
import app,leveling
from companion_widgets import ui_walk_widgets
from companion_feature_model import utility_session_toggle
parser=argparse.ArgumentParser();parser.add_argument('--minutes',type=float,default=150);parser.add_argument('--report',type=Path);args=parser.parse_args()
project=Path(__file__).resolve().parents[1];report=args.report.resolve() if args.report else project.parent/'training-persistent-soak.json'
app.App.sync_from_game=lambda *a,**k:None;app.App.prefetch=lambda *a,**k:None;app.App.run_bg=lambda *a,**k:None
class NoHotkey:
 def __init__(self,*a,**k):pass
 def start(self):pass
app.HotkeyThread=NoHotkey
source_sha=__import__('hashlib').sha256(b''.join(p.read_bytes() for p in sorted(project.glob('*.py')))).hexdigest()
start=time.monotonic();errors=[];frame=0;history=[];expected_money=0;samples=[];baseline=None;had_gap=False
with tempfile.TemporaryDirectory(prefix='persistent-training-',dir=project.parent) as folder:
 app.STATE_FILE=str(Path(folder)/'state.json')
 Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'auto_on_v2':True,'training_auto_context':False,'level':27,'active':[],'training_target':'23','training_personal_gain':9,'map':'010005073'}))
 root=tk.Tk();root.report_callback_exception=lambda x,y,z:errors.append(str(y));a=app.App(root);a.db.load_indexes();a.ui_tools();root.withdraw();a._tools_window.withdraw()
 a.state['utility_session'].update(running_since=time.time(),exp=0,kills=0,mesos=0,cost=25)
 def snapshot(running=True):
  global baseline
  gc.collect();s=a.state['utility_session'];r={'seconds':round(time.monotonic()-start,1),'frames':frame,'exp':s.get('exp'),'party_seen':s.get('party_exp',0),'mesos_observed':s.get('mesos'),'mesos_true':expected_money,'fonts':len(root.tk.call('font','names')),'images':len(root.tk.call('image','names')),'jobs':len(root.tk.call('after','info')),'callback_errors':len(errors)}
  if baseline is None and frame>10:baseline=r
  if baseline:
   for key,tolerance in [('fonts',10),('images',10),('jobs',8)]:
    if r[key]>baseline[key]+tolerance:raise AssertionError('Resource growth: '+key)
  samples.append(r);report.write_text(json.dumps({'running':running,'source_sha':source_sha,'target_seconds':args.minutes*60,'ok':not errors,'latest':r,'samples':samples,'errors':errors,'scope':'Persistent own Tk UI; synthetic EXP, party and mesos notifications with periodic log gaps. No game capture, hotkeys or gameplay input.'},indent=2))
  print(json.dumps(r),flush=True)
 def run(fn,callback,on_error=None):
  global frame,expected_money,had_gap
  frame+=1;m=10+frame%11;history.extend([('exp',7),('bonus',2),('mesos',m)])
  if frame>1:expected_money+=m
  events=history[-15:];gap=frame%97==0
  if gap:events=None;had_gap=True
  lv=27;exp=1000+frame*9
  while exp>=leveling.exp_to_next(lv):exp-=leveling.exp_to_next(lv);lv+=1
  reading={'level':lv,'exp':exp,'percent':leveling.percent(exp,lv),'need':leveling.exp_to_next(lv),'source':'Synthetic fixture'}
  def deliver():
   callback({'events':events,'character':reading})
   s=a.state['utility_session']
   if frame>=2 and s['exp']!=9*(frame-1):raise AssertionError(f'EXP drift: {s["exp"]} != {9*(frame-1)}')
   if s['mesos']>expected_money:raise AssertionError('Mesos overcount')
   if not had_gap and not expected_money-m<=s['mesos']<=expected_money:raise AssertionError('Mesos drift beyond one confirming frame')
   f=a.training_forecast_now()
   if frame>=2 and (not f['available'] or f['kills']!=__import__('math').ceil((leveling.exp_to_next(lv)-exp)/9)):raise AssertionError('Kills-to-level drift')
  root.after(20,deliver)
 a.run_bg=run;a.utility_poll_rewards();next_report=start+30
 try:
  while time.monotonic()-start<args.minutes*60:
   root.update()
   if errors:raise AssertionError(errors[-1])
   if time.monotonic()>=next_report:snapshot();next_report=time.monotonic()+60
   time.sleep(.03)
  snapshot(False)
 except Exception as exc:
  errors.append(str(exc));snapshot(False);raise
 finally:root.destroy()
