"""Docked GPS on the supplied minimap frames. Own windows only, no game input."""
from pathlib import Path
import os,sys,json,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
import tkinter as tk
import app,game_sync
app.App.sync_from_game=lambda self,*a,**k:None
app.App.prefetch=lambda self:None
class NoHotkey:
    def __init__(self,*a,**k):pass
    def start(self):pass
app.HotkeyThread=NoHotkey
checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)
here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='gps-dock-',dir=here) as folder:
    app.STATE_FILE=os.path.join(folder,'state.json')
    Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'auto_on_v2':True,'active':[],'level':26,'map':'010005061','gps_alpha':1.0,'idle_alpha':1.0,'panel_size':[470,640],'compact_v3':True}),encoding='utf-8')
    root=tk.Tk();root.withdraw();a=app.App(root);a.db.load_indexes();root.update()
    errors=[];root.report_callback_exception=lambda x,y,z:errors.append(str(y))
    for filename,map_id in [('henesys_gps_masked.png','010001000'),('live_frame_ant_tunnel2.png','010005061'),('live_frame_1920.png','010005061')]:
        frame=game_sync.find_minimap(Image.open(here/filename).convert('RGB'))
        check('Minimap frame detected: '+filename,frame is not None)
        a._minimap=tuple(value+(620 if index%2==0 else 132) for index,value in enumerate(frame))
        a.state['map']=map_id;a.state['gps_docked']=True
        a.start_route('dock-test','010004000');a._dock_gps_now();root.update()
        mm=a._minimap
        check('GPS aligned to minimap right edge: '+filename,(a.gps.winfo_x(),a.gps.winfo_y())==(mm[2]+1,mm[1]))
        check('GPS height follows minimap: '+filename,abs(a.gps.winfo_height()-(mm[3]-mm[1]+1))<=1)
        view=a.gps_view('dock-test',with_map=False)
        check('Next map and step count visible: '+filename,bool(view.get('dest')) and 'step 1 of' in view.get('step',''))
    a.full_routes.add('dock-test')
    view=a.gps_view('dock-test',with_map=False)
    route=a.db.route(a.state['map'],'010004000',a.cabs())
    check('Every intermediate map remains available',len(view.get('steps',[]))==len(route) and len(route)>1)
    a.state['gps_docked']=False
    pos=(a.gps.winfo_x(),a.gps.winfo_y());a._minimap=(10,20,350,290);a._dock_gps_now();root.update()
    check('Manual undocking keeps saved position',(a.gps.winfo_x(),a.gps.winfo_y())==pos)
    a.dock_gps();root.update()
    check('Dock action restores minimap anchor',(a.gps.winfo_x(),a.gps.winfo_y())==(351,20))
    check('No callback errors',not errors)
    a.close_gps()
    for job in root.tk.call('after','info'):root.tk.call('after','cancel',job)
    root.destroy()
report={'ok':True,'count':len(checks),'checks':checks,'scope':'Static supplied minimap frames and own GUI windows; no traversal or gameplay input.'}
(here/'gps-docking-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
