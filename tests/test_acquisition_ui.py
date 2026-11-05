from pathlib import Path
import sys,os,json,tempfile,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
import app
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
    for _ in range(4):root.update();time.sleep(.02)
def texts(parent):return [w.cget('text') for w in ui_walk_widgets(parent) if isinstance(w,(tk.Label,tk.Button))]
fixture=json.loads(Path(__file__).with_name('real-item-source-fixtures.json').read_text())
with tempfile.TemporaryDirectory(prefix='acquisition-',dir=Path(__file__).parent) as folder:
    app.STATE_FILE=os.path.join(folder,'state.json')
    Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'auto_on_v2':True,'active':['10113'],'expanded':'10113','level':27,'map':'010005000','done':{'10113':[0,1,3,4]},'progress':{'10113':{'2':0}}}),encoding='utf-8')
    root=tk.Tk();errors=[];root.report_callback_exception=lambda x,y,z:errors.append(str(y))
    a=app.App(root);a.db.load_indexes();a.rank_droppers=lambda *a:[]
    a.db.item_acquisition_sources=lambda iid,name:fixture.get(name,[])
    a.guides['10113']=a._resolve_guide(a.db.quests['10113'])
    def unavailable_drops(*args):raise ConnectionError('fixture drop lookup unavailable')
    a.rank_droppers=unavailable_drops
    check('Shop sources survive unavailable monster-drop lookup',bool(a._resolve_guide(a.db.quests['10113'])[2]['sources']))
    a.rank_droppers=lambda *args:[]
    routes=[];a.start_route=lambda *args,**kwargs:routes.append((args,kwargs))
    for scale in (1.0,1.3):
        a.set_text_size(scale);a.render();pump()
        shown=texts(a.scroll.inner)
        check('Salad buying instruction visible at '+str(scale),any('Buy: 24 Hr Mobile Store' in t and '220' in t and 'Ant Tunnel Park' in t for t in shown))
        check('No misleading monster-only note',not any('Not a monster drop' in t for t in shown))
    button=next(w for w in ui_walk_widgets(a.scroll.inner) if isinstance(w,tk.Label) and w.cget('text')=='GPS')
    button.event_generate('<Button-1>');pump()
    check('Shop GPS targets correct map and NPC',routes[-1][0]==('10113','010005070',None,'24 Hr Mobile Store'))
    a.open_acquisition_sources('10113',a.guides['10113'][2]);pump()
    dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'Sources' in w.title())
    check('Alternate shops show citizenship requirement',any('Visitor required' in t for t in texts(dialog)));dialog.destroy()
    a.state.update(active=['10407'],expanded='10407',map='010002000',done={},progress={})
    a.guides['10407']=a._resolve_guide(a.db.quests['10407']);a.render();pump()
    check('Betty objective shows plant instructions',any('Break / collect: Ellinia Flower' in t for t in texts(a.scroll.inner)))
    a.open_acquisition_sources('10407',a.guides['10407'][0]);pump()
    dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'Sources' in w.title())
    check('All five plant maps are available',sum('Break / collect: Ellinia Flower' in t for t in texts(dialog))==5);dialog.destroy()
    a.state['done']={'10407':[0]};a.render();pump()
    check('Completed objectives do not show collection instructions',not any('Break / collect:' in t for t in texts(a.scroll.inner)))
    check('No callback errors',not errors)
    for job in root.tk.call('after','info'):root.tk.call('after','cancel',job)
    root.destroy()
report={'ok':True,'count':len(checks),'checks':checks}
Path(__file__).with_name('acquisition-ui-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
