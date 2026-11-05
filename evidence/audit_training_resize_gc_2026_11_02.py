from pathlib import Path
import sys,os,json,tempfile,time
sys.path.insert(0,str(Path(__file__).resolve().parent/'umbrale-companion'))
import tkinter as tk
import app
import companion_portraits
real_fetch=companion_portraits.fetch_portrait
companion_portraits.fetch_portrait=lambda db,kind,identity,name:real_fetch(db,kind,identity,name) if (kind,str(identity)) in (("mob","23"),("npc","226")) else None
from companion_widgets import ui_walk_widgets
app.App.run_bg=lambda *a,**k:None
app.App.sync_from_game=lambda *a,**k:None
app.App.prefetch=lambda *a,**k:None
class NoHotkey:
    def __init__(self,*a,**k):pass
    def start(self):pass
app.HotkeyThread=NoHotkey
checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)
def pump():
    for _ in range(4):root.update();time.sleep(.015)
def texts(w):return [c.cget('text') for c in ui_walk_widgets(w) if isinstance(c,(tk.Label,tk.Button))]
with tempfile.TemporaryDirectory(prefix='map-reward-',dir=Path(__file__).parent) as folder:
    app.STATE_FILE=os.path.join(folder,'state.json')
    Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'auto_on_v2':True,'active':['10113'],'expanded':'10113','level':27,'map':'010005000','done':{'10113':[0]}}),encoding='utf-8')
    root=tk.Tk();errors=[];root.report_callback_exception=lambda x,y,z:errors.append(str(y))
    a=app.App(root);a.db.load_indexes()



    import leveling,hashlib,gc
    snapshots=[]
    a.state.update(training_auto_context=False,training_target='23',party=1,training_personal_gain=100000)
    for scale in (1.0,1.15,1.3,1.0):
        a.set_text_size(scale);pump()
        original=None
        for n in range(50):
            a.training_accept_character({'level':27,'exp':leveling.exp_to_next(27)-1-n})
            check('One event exceeds remaining EXP',a.training_forecast_now()['kills']==1)
            nodes=tuple(str(v) for v in ui_walk_widgets(a.lvl_strip))
            if original is None:original=nodes
            else:check('Stable nodes while EXP changes',nodes==original)
            root.update_idletasks()
        gc.collect();pump()
        snapshots.append(dict(scale=scale,widgets=len(nodes),fonts=len(root.tk.call('font','names')),images=len(root.tk.call('image','names'))))
    check('Fonts bounded after collection',max(row['fonts'] for row in snapshots)-min(row['fonts'] for row in snapshots)<=5)
    check('No callback errors',not errors)
    report=dict(ok=True,updates=200,snapshots=snapshots,scope='Isolated native Tk with simulated EXP and text resizing; no capture/input')
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));root.destroy()
