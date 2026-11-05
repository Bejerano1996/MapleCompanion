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
    for _ in range(4):root.update();time.sleep(.015)
def texts(w):return [c.cget('text') for c in ui_walk_widgets(w) if isinstance(c,(tk.Label,tk.Button))]
with tempfile.TemporaryDirectory(prefix='map-reward-',dir=Path(__file__).parent) as folder:
    app.STATE_FILE=os.path.join(folder,'state.json')
    Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'auto_on_v2':True,'active':['10113'],'expanded':'10113','level':27,'map':'010005000','done':{'10113':[0]}}),encoding='utf-8')
    root=tk.Tk();errors=[];root.report_callback_exception=lambda x,y,z:errors.append(str(y))
    a=app.App(root);a.db.load_indexes()
    a.guides['10113']=[{'name':'Jr. Necki','lines':[]},{'name':'Stirge','lines':[{'mob':17,'maps':[]}]},{'name':'Salad','sources':[]},{'name':'Skin','lines':[]},{'name':'Wing','lines':[{'mob':17,'maps':[]}]}]
    routes=[];a.start_route=lambda *args,**kwargs:routes.append((args,kwargs))
    for scale in (1.0,1.3):
        a.set_text_size(scale);a.render();pump();shown=texts(a.scroll.inner)
        check('Inline spawn and distance at '+str(scale),any(t.startswith('Spawn ') and 'portals' in t for t in shown))
        check('Spawn and nearest selectors available at '+str(scale),'Spawn' in shown and 'Nearest' in shown)
    a.set_objective_map_sort('near');pump()
    check('Sort preference persists',json.loads(Path(app.STATE_FILE).read_text())['objective_map_sort']=='near')
    group={'mob':17,'maps':[]};a.open_monster_maps('10113',group);pump()
    dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'Maps ·' in w.title())
    from monster_maps_ui import monster_map_rows
    rows=monster_map_rows(a,group)
    destination=next(w for w in ui_walk_widgets(dialog) if isinstance(w,tk.Label) and w.cget('text')==rows[0]['name'])
    destination.event_generate('<Button-1>');pump()
    check('Clicking a map routes to the map and the correct monster',routes[-1][0]==('10113',rows[0]['map'],17))
    check('All maps dialog contains the full known list',sum(t.startswith('Spawn ') for t in texts(dialog))==len(rows))
    a.state['map']=rows[0]['map']
    until=time.monotonic()+1.15
    while time.monotonic()<until:root.update();time.sleep(.02)
    check('Open map list updates distance as your map changes',any(t.startswith('Spawn ') and 'Here' in t for t in texts(dialog)))
    check('Selected sort mode is marked','✓ Nearest' in texts(dialog));dialog.destroy()
    a.open_quest_rewards('10113');pump()
    dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'Rewards ·' in w.title())
    shown=texts(dialog)
    check('EXP and mesos are named',any('1,380 EXP' in t for t in shown) and any('614 mesos' in t for t in shown))
    check('Random gems and their chances are visible',any('Garnet' in t and '12.5%' in t for t in shown) and any('not guaranteed' in t for t in shown));dialog.destroy()
    a.state['expanded']=None;a.render();pump()
    check('Collapsed quest still has reward details','Rewards…' in texts(a.scroll.inner))
    check('No callback errors',not errors)
    for job in root.tk.call('after','info'):root.tk.call('after','cancel',job)
    root.destroy()
report={'ok':True,'count':len(checks),'checks':checks}
Path(__file__).with_name('maps-rewards-ui-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
