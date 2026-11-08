from pathlib import Path
import sys,os,json,tempfile,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
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

    a.state['tab']='pq';a._companion_data_error='offline';a.render();pump()
    check('PQ works with unavailable indexes','Kerning City PQ' in texts(a.scroll.inner))
    a._companion_data_error=None
    a.state['tab']='mobs';a.mob_query.set('evil eye');a.state['mob_open']=23;a.render();pump()
    shown=texts(a.scroll.inner)
    check('Normal Evil Eye visible','Evil Eye' in shown)
    check('Job variants hidden',not any('Job Test' in t for t in shown))
    import mesowatch_browser
    opened=[];mesowatch_browser.launch_search=lambda name:opened.append(name)
    a.ui_mesowatch('Salad');pump()
    w=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'MesoWatch' in w.title())
    next(b for b in ui_walk_widgets(w) if isinstance(b,tk.Button) and b.cget('text')=='Search MesoWatch ↗').invoke();pump()
    check('Search opens canonical MesoWatch',opened==['Salad'])
    check('Monster thumbnail loaded',('mob','23',32) in a._portraits.images)
    a.state['tab']='quests';a.render();
    until=time.monotonic()+.7
    while time.monotonic()<until:root.update();time.sleep(.02)
    check('Quest NPC thumbnail loaded',('npc','226',28) in a._portraits.images)
    check('Price icon is rendered',bool(a.price_btn.cget('image')))
    check('No callback exceptions',not errors)
    print(json.dumps({'ok':True,'checks':checks}));root.destroy()
