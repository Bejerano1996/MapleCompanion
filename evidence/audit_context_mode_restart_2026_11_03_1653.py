from pathlib import Path
import sys,tempfile,os,json,hashlib,tkinter as tk
from unittest.mock import patch
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import app,leveling,training_ui,training_context,copy,time
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
  for seed in range(20):
   a.state['utility_session']=dict(id=str(seed),running_since=1,auto_rewards=True,exp=42)
   a.state['training_auto_context']=True;a._context_busy=False;a._context_last_poll=-100
   a.db.maps={'a':{},'b':{}}
   training_context.context_poll(a);assert len(pending)==1
   old=pending.pop()
   for _ in range(2):
    training_ui.training_setup(a);window=a._training_setup_window;window.withdraw()
    entries=[w for w in ui_walk_widgets(window) if type(w) is tk.Entry]
    for entry,value in zip(entries,('27','','','')):entry.delete(0,'end');entry.insert(0,value)
    next(w for w in ui_walk_widgets(window) if isinstance(w,tk.Checkbutton)).invoke()
    next(w for w in ui_walk_widgets(window) if isinstance(w,tk.Button) and w.cget('text')=='Apply').invoke()
    assert not window.winfo_exists()
   assert a.state['training_auto_context'] is True
   before=copy.deepcopy(a._training_context);session=copy.deepcopy(a.state['utility_session'])
   old(dict(game=True,map='a',mobs=[23],party_visible=2,captured_at=100.))
   assert a._training_context==before and a.state['utility_session']==session,'Old context survived off/on Setup'
   assert not a._context_busy
   a.set_location=lambda m:a.state.update(map=m)
   for _ in range(2):
    a._context_last_poll=-100;training_context.context_poll(a);assert len(pending)==1
    pending.pop()(dict(game=True,map='b',mobs=[24],party_visible=3,captured_at=time.time()))
   assert a._training_context['map']=='b' and a._training_context['party_visible']==3
   assert set(a.state['utility_session']['observed_monsters'])=={'24'}
   assert a.state['utility_session']['exp']==42
   cases+=1
 root.update_idletasks();assert not errors,errors
 report=dict(ok=True,cases=cases,off_on_cycles=20,old_context_rejected=20,tk_errors=errors,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Full isolated native CompanionApp real general sync dispatch/result pump/character accept and parsed HUD. Controlled callbacks, temporary state, no capture/network/hotkeys/live game.')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));root.destroy()

