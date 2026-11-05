from pathlib import Path
import sys,tempfile,os,json,hashlib,tkinter as tk
from unittest.mock import patch
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import app,leveling,training_ui
from companion_widgets import ui_walk_widgets
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
  for seed in range(20):
   a.training_accept_character({'level':27,'exp':2000});a._reads={}
   dispatch(28,1000)
   assert a.state['character_exp']['level']==27
   key=('validated-character-level',)
   assert a._reads[key]==(28,1)
   training_ui.training_setup(a);window=a._training_setup_window;window.withdraw()
   entries=[w for w in ui_walk_widgets(window) if type(w) is tk.Entry]
   for entry,value in zip(entries,('27','2000','','')):entry.delete(0,'end');entry.insert(0,value)
   next(w for w in ui_walk_widgets(window) if isinstance(w,tk.Button) and w.cget('text')=='Apply').invoke()
   assert not window.winfo_exists()
   assert key not in a._reads
   assert a.state['character_exp']['source']=='Manual calibration'
   dispatch(28,1000)
   assert a.state['character_exp']['level']==27, 'Old confirmation survived contradictory accepted level'
   assert a._reads[key]==(28,1)
   dispatch(28,1000)
   assert a._reads[key]==(28,2)
   assert a.state['character_exp']['level']==28
   cases+=1
 root.update_idletasks();assert not errors,errors
 report=dict(ok=True,cases=cases,actual_setup_apply=20,first_new_level_not_accepted=20,second_new_level_accepted=20,tk_errors=errors,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Full isolated native CompanionApp real general sync dispatch/result pump/character accept and parsed HUD. Controlled callbacks, temporary state, no capture/network/hotkeys/live game.')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));root.destroy()

