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
from companion_feature_model import utility_session_toggle
from session_reader import RewardRead
import companion_tools
cases=0;errors=[]
with tempfile.TemporaryDirectory(prefix='resume-visible-rewards-',dir=rootpath.parent) as folder:
 app.STATE_FILE=str(Path(folder)/'state.json')
 for exp in (-1000,-1,0,1,500):
  writer=object.__new__(app.App);writer.set_status=lambda *args:None
  writer.state={'auto_sync':False,'active':[],'training_auto_context':False,'level':27,'character_exp':{'level':27,'exp':1000},'utility_session':dict(id=str(cases),elapsed=10.,running_since=900.,exp=exp,kills=7,party_exp=17,mesos=80,cost=90)}
  with patch('time.time',return_value=1000.):writer.save_state()
  root=tk.Tk();root.withdraw();root.report_callback_exception=lambda k,e,t:errors.append(str(e));a=app.App(root);root.withdraw()
  assert a.state['utility_session']['running_since'] is None
  assert a.state['utility_session']['elapsed']==110.
  a.state['utility_session']=utility_session_toggle(a.state['utility_session'],9000.)
  pending=[];a.run_bg=lambda work,loaded,on_error:pending.append(loaded)
  # Poll dispatch is explicit; GUI after callbacks remain queued until root destruction.
  clock=[9000.]
  with patch('time.time',side_effect=lambda:clock[0]),patch('time.monotonic',side_effect=lambda:clock[0]):
   def read(events,value):
    clock[0]+=.2;companion_tools.utility_poll_rewards(a);assert len(pending)==1
    pending.pop()({'events':RewardRead(events,False),'character':{'level':27,'exp':value}})
   old=[('exp',7),('bonus',2),('mesos',17)]
   read(old,2000);read(old,2000)
   session=a.state['utility_session'];assert (session['exp'],session['party_exp'],session['kills'],session['mesos'])==(exp,17,7,80)
   fresh=old+[('exp',11),('bonus',3),('mesos',31)]
   read(fresh,2014);read(fresh,2014)
   for _ in range(3):read(fresh,2014)
   assert (session['exp'],session['party_exp'],session['kills'],session['mesos'])==(exp+14,20,8,111)
   a.save_state()
   persisted=json.loads(Path(app.STATE_FILE).read_text())['utility_session']
   assert (persisted['exp'],persisted['party_exp'],persisted['kills'],persisted['mesos'])==(exp+14,20,8,111)
   assert persisted['running_since'] is None
  root.update_idletasks();root.destroy();cases+=1
assert not errors,errors
report=dict(ok=True,cases=cases,prior_net_exp=[-1000,-1,0,1,500],old_visible_notices_rebased=True,new_exp=14,new_party=3,new_events=1,new_money=31,tk_errors=errors,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Actual save/reload native CompanionApp, resumed production reward callback/accountant with syntheticoldvisible+newnotices and HUD; tempstate only,no game/capture/network/hotkeys')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
