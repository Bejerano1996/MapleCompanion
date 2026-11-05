from pathlib import Path
import sys,tempfile,os,json,hashlib,tkinter as tk
from unittest.mock import patch
rootpath=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(rootpath))
import app
app.App.run_bg=lambda *args,**kwargs:None;app.App.sync_from_game=lambda *args,**kwargs:None;app.App.prefetch=lambda *args,**kwargs:None
class NoHotkey:
 def __init__(self,*a,**k):pass
 def start(self):pass
app.HotkeyThread=NoHotkey
with tempfile.TemporaryDirectory(prefix='missing-game-sync-',dir=rootpath.parent) as folder:
 app.STATE_FILE=str(Path(folder)/'state.json');Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'active':[]}))
 root=tk.Tk();root.withdraw();errors=[];root.report_callback_exception=lambda k,e,t:errors.append(str(e));a=app.App(root);root.withdraw();received=[]
 a.syncing=True;a._on_synced(None);assert not a.syncing and a._live_last_result['_minimap_readable'] is False
 for _ in range(50):a.results.put((a._on_synced,None,None))
 a.results.put((lambda value:received.append(value),16,None))
 exists=app.os.path.exists
 with patch.object(app.os.path,'exists',side_effect=lambda p:False if os.fspath(p)==os.fspath(app.SHOW_REQUEST) else exists(p)):
  for _ in range(100):
   if a.results.empty():break
   a._poll()
 assert received==[16] and a.results.empty() and not a.syncing
 root.update_idletasks();assert not errors,errors
 report=dict(ok=True,missing_game_callbacks=51,subsequent_result_processed=True,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rootpath.glob('*.py')))).hexdigest(),scope='Isolated fullnativeCompanionApp,backgroundcapture/hotkeys/networkdisabled,tempstateonly; realmissinggamesync+sharedresultpump, no livegame')
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));root.destroy()
