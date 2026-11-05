from pathlib import Path
import sys,tempfile,os,json,hashlib,tkinter as tk
from unittest.mock import patch
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import app,leveling,copy
real_sync=app.App.sync_from_game
app.App.run_bg=lambda *args,**kwargs:None
app.App.sync_from_game=lambda *args,**kwargs:None
app.App.prefetch=lambda *args,**kwargs:None
class NoHotkey:
 def __init__(self,*a,**k):pass
 def start(self):pass
app.HotkeyThread=NoHotkey
with tempfile.TemporaryDirectory(prefix='sync-same-value-',dir=rootpath.parent) as folder:
 app.STATE_FILE=str(Path(folder)/'state.json');Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'active':[]}))
 root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda k,e,t:errors.append(str(e))
 a=app.App(root);root.withdraw();pending=[];cases=0
 a.run_bg=lambda work,callback,on_error:pending.append(callback)
 a.db.quests=a.db.quests or {'audit':{}}
 exists=app.os.path.exists
 with patch.object(app.os.path,'exists',side_effect=lambda p:False if os.fspath(p)==os.fspath(app.SHOW_REQUEST) else exists(p)):
  def dispatch(level,exp,intervene=False):
   a._exp_tick=app.EXP_BAR_EVERY-1;a.syncing=False;real_sync(a,auto=True)
   assert len(pending)==1
   if intervene:a.training_accept_character({'level':27,'exp':2000})
   texts=[f'LV.{level}',f'EXP {exp}',f'{leveling.percent(exp,level):.2f}%']
   result={'auto':True,'full':False,'quests':[],'tracked':[],'progress':{},'window':True,'exp_bar':texts,'map':None}
   a.results.put((pending.pop(),result,None));a._poll()
   assert not a.syncing and a.results.empty()
  missing_polls=0
  for seed in range(60):
   a.training_accept_character({'level':27,'exp':2000});a._reads={};a._training_level_confirmation_at=None
   target=27 if seed%2 else 28;value=2016 if target==27 else 1000
   counters=copy.deepcopy(a.state.get('utility_session'))
   clock=[100.]
   with patch('time.monotonic',side_effect=lambda:clock[0]):
    dispatch(target,value)
    assert a.state['character_exp']['exp']==2000
    first_at=a._training_level_confirmation_at
    for i in range((10,30,100)[seed%3]):
     clock[0]+=2.
     a._exp_tick=app.EXP_BAR_EVERY-1;real_sync(a,auto=True)
     result=None if i%3==0 else {'auto':True,'full':False,'quests':[],'tracked':[],'progress':{},'window':True,'exp_bar':[] if i%3==1 else ['EXP 1000'],'map':None}
     a.results.put((pending.pop(),result,None));a._poll()
     assert a._training_level_confirmation_at==first_at
     assert a.state['character_exp']['exp']==2000
     assert a.state.get('utility_session')==counters
     missing_polls+=1
    clock[0]+=1.;dispatch(target,value)
    assert a.state['character_exp']['exp']==2000
    clock[0]+=1.;dispatch(target,value)
    assert a.state['character_exp']['level']==target and a.state['character_exp']['exp']==value
    assert a.state.get('utility_session')==counters
   cases+=1
 root.update_idletasks();assert not errors,errors
 report=dict(ok=True,cases=cases,missing_polls=missing_polls,same_level_cases=30,new_level_cases=30,session_counters_unchanged=True,tk_errors=errors,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Full isolated native CompanionApp real general sync dispatch/result pump/character accept and parsed HUD. Controlled callbacks, temporary state, no capture/network/hotkeys/live game.')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));root.destroy()

