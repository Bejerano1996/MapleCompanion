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
with tempfile.TemporaryDirectory(prefix='general-sync-native-',dir=rootpath.parent) as folder:
 app.STATE_FILE=str(Path(folder)/'state.json');Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'active':[]}))
 root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda k,e,t:errors.append(str(e))
 a=app.App(root);root.withdraw();pending=[];cases=0
 a.run_bg=lambda work,callback,on_error:pending.append(callback)
 a.db.quests=a.db.quests or {'audit':{}}
 exists=app.os.path.exists
 with patch.object(app.os.path,'exists',side_effect=lambda p:False if os.fspath(p)==os.fspath(app.SHOW_REQUEST) else exists(p)):
  for seed in range(40):
   a.training_accept_character({'level':27,'exp':1000})
   a.syncing=False;real_sync(a,auto=False);assert len(pending)==1
   newer=seed%2==0
   if newer:a.training_accept_character({'level':27,'exp':2000+seed})
   revision=a._character_read_revision
   texts=['LV.27','EXP 1016',f'{leveling.percent(1016,27):.2f}%']
   result={'auto':False,'full':False,'quests':[],'tracked':[],'progress':{},'window':True,'exp_bar':texts,'map':None,'map_text':'audit evidence'}
   a.results.put((pending.pop(),result,None));a._poll()
   expected=2000+seed if newer else 1016
   assert a.state['character_exp']['exp']==expected,(seed,a.state['character_exp'])
   assert a._character_read_revision==revision+(0 if newer else 1)
   assert a._last_read[0]=='audit evidence'
   assert not a.syncing and a.results.empty()
   assert result['exp_bar']==texts
   cases+=1
 root.update_idletasks();assert not errors,errors
 report=dict(ok=True,cases=cases,stale_dropped=20,current_accepted=20,map_text_processed=40,tk_errors=errors,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Full isolated native CompanionApp real general sync dispatch/result pump/character accept and parsed HUD. Controlled callbacks, temporary state, no capture/network/hotkeys/live game.')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));root.destroy()

