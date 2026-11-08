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


    a.state['tab']='mobs';a.mob_query.set('evil eye');a.state['mob_open']=None
    for width in (340,360,480):
        for scale in (1.0,1.15,1.3):
            a.set_text_size(scale);a.state['panel_size']=[width,600];root.geometry(f'{width}x600+80+80');pump();a.render();pump()
            widgets=list(ui_walk_widgets(a.scroll.inner))
            name=next(v for v in widgets if isinstance(v,tk.Label) and v.cget('text')=='Evil Eye')
            stats=next(v for v in widgets if isinstance(v,tk.Label) and 'HP ·' in v.cget('text'))
            check(f'Stats below name {width}/{scale}',stats.winfo_rooty()>=name.winfo_rooty()+name.winfo_height())
            for view in (name,stats):
                check(f'Text fits {width}/{scale}',view.winfo_rootx()+view.winfo_width()<=a.scroll.inner.winfo_rootx()+a.scroll.inner.winfo_width())
    check('No callback errors',not errors);print(json.dumps({'ok':True,'checks':len(checks)}));root.destroy()
