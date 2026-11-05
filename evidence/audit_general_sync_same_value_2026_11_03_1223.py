from pathlib import Path
import sys,tempfile,os,json,hashlib,tkinter as tk
from unittest.mock import patch
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import app,leveling
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
  for seed in range(100):
   value=2000+seed
   a.training_accept_character({'level':27,'exp':value})
   a.syncing=False;real_sync(a,auto=False);assert len(pending)==1
   # A repeated accepted value is still newer evidence and invalidates the older capture.
   a.training_accept_character({'level':27,'exp':value})
   revision=a._character_read_revision
   texts=['LV.27',f'EXP {value-16}',f'{leveling.percent(value-16,27):.2f}%']
   result={'auto':False,'full':False,'quests':[],'tracked':[],'progress':{},'window':True,'exp_bar':texts,'map':None,'map_text':'audit evidence'}
   a.results.put((pending.pop(),result,None));a._poll()
   assert a.state['character_exp']['exp']==value
   assert a._character_read_revision==revision
   # Dispatch again after calibration: unchanged EXP must now be accepted, not permanently blocked.
   real_sync(a,auto=False);assert len(pending)==1
   texts=['LV.27',f'EXP {value}',f'{leveling.percent(value,27):.2f}%']
   fresh=dict(result,exp_bar=texts)
   a.results.put((pending.pop(),fresh,None));a._poll()
   assert a.state['character_exp']['exp']==value
   assert a._character_read_revision==revision+1
   assert not a.syncing and a.results.empty()
   assert a._last_read[0]=='audit evidence'
   cases+=1
 root.update_idletasks();assert not errors,errors
 report=dict(ok=True,cases=cases,stale_dropped=100,current_same_value_accepted=100,map_text_processed=200,tk_errors=errors,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Full isolated native CompanionApp real general sync dispatch/result pump/character accept and parsed HUD. Controlled callbacks, temporary state, no capture/network/hotkeys/live game.')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));root.destroy()

