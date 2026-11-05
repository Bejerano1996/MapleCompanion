"""Time-based UI lifecycle check, isolated from game capture and global hotkeys.

Run from the project directory: python tests/soak_compact_ui.py --minutes 120
Uses cached map indexes. Never launches the game or sends gameplay input.
"""
from pathlib import Path
import sys,os,json,time,tempfile,argparse,gc
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
import app,widgets
parser=argparse.ArgumentParser();parser.add_argument('--minutes',type=float,default=120)
parser.add_argument('--interval',type=float,default=15)
args=parser.parse_args()
app.App.sync_from_game=lambda *a,**k:None
app.App.prefetch=lambda *a,**k:None
app.App.run_bg=lambda *a,**k:None
app.find_game_window=lambda:None
class NoHotkey:
    def __init__(self,*a,**k):pass
    def start(self):pass
app.HotkeyThread=NoHotkey
here=Path(__file__).parent
report_path=here/'compact-soak-results.json'
start=time.monotonic();cycle=0;errors=[];samples=[]
def pump():
    for _ in range(3):root.update();time.sleep(.015)
def stats():
    gc.collect()
    return {'cycles':cycle,'elapsed_seconds':round(time.monotonic()-start,1),
            'font_objects':len(root.tk.call('font','names')),
            'image_objects':len(root.tk.call('image','names')),
            'scheduled_jobs':len(root.tk.call('after','info')),
            'toplevels':sum(isinstance(w,tk.Toplevel) for w in root.winfo_children()),
            'callback_errors':len(errors)}
with tempfile.TemporaryDirectory(prefix='compact-soak-',dir=here) as folder:
    app.STATE_FILE=os.path.join(folder,'state.json')
    Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'auto_on_v2':True,'level':26,'map':'010005061','active':['10306'],'tracked':['10306'],'panel_size':[360,520],'companion_compact_v2':True,'idle_alpha':1.0}),encoding='utf-8')
    root=tk.Tk();root.withdraw();root.report_callback_exception=lambda x,y,z:errors.append(str(y))
    a=app.App(root);a.db.load_indexes();pump()
    baselines={}
    try:
        while time.monotonic()-start<args.minutes*60:
            cycle+=1
            a.set_text_size(widgets.TEXT_SCALES[cycle%3])
            a.set_tab(app.TABS[cycle%len(app.TABS)][0]);pump()
            a.ui_focus_search();pump();a.ui_close_search()
            a.companion_exp_details();a.set_party(cycle%6+1);pump();a._companion_exp_window.destroy()
            a.ui_settings();pump()
            for window in list(root.winfo_children()):
                if isinstance(window,tk.Toplevel):window.destroy()
            a.ui_tools();pump();a._utility_show(('session','route','timers','saved','compare','quick')[cycle%6]);pump();a._tools_window.destroy()
            a._minimap=(20,30,280,240)
            a.state['gps_docked']=True;a.start_route('soak','010004000');pump()
            if (a.gps.winfo_x(),a.gps.winfo_y())!=(281,30):raise AssertionError('GPS lost its minimap anchor')
            a.close_gps();a.stop_route('soak');pump()
            snapshot=stats()
            scenario=cycle%30
            baseline=baselines.get(scenario)
            if baseline is None:baselines[scenario]=snapshot
            if errors:raise AssertionError('Tk callback error: '+errors[0])
            if baseline and cycle>30:
                for key,allowance in [('font_objects',15),('image_objects',12),('scheduled_jobs',8),('toplevels',0)]:
                    if snapshot[key]>baseline[key]+allowance:raise AssertionError('Resource growth: '+key)
            samples.append(snapshot)
            report_path.write_text(json.dumps({'ok':None,'running':True,'latest':snapshot,'samples':samples,'errors':errors},indent=2),encoding='utf-8')
            print(json.dumps(snapshot),flush=True)
            deadline=min(start+args.minutes*60,time.monotonic()+args.interval)
            while time.monotonic()<deadline:root.update();time.sleep(.1)
        report={'ok':True,'running':False,'latest':stats(),'samples':samples,'errors':errors,'scope':'Own fixture windows; no game capture, hotkeys or gameplay input.'}
        report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('SOAK PASS '+json.dumps(report['latest']),flush=True)
    except Exception as exc:
        report_path.write_text(json.dumps({'ok':False,'running':False,'latest':stats(),'errors':errors,'failure':str(exc),'samples':samples},indent=2),encoding='utf-8')
        raise
    finally:
        for job in root.tk.call('after','info'):root.tk.call('after','cancel',job)
        root.destroy()
