"""Check action buttons at every text size and the Tools window's minimum width."""
from pathlib import Path
import sys,os,json,tempfile,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
import app,widgets
from companion_widgets import ui_walk_widgets
app.App.sync_from_game=lambda *a,**k:None
app.App.prefetch=lambda *a,**k:None
app.App.run_bg=lambda *a,**k:None
class NoHotkey:
    def __init__(self,*a,**k):pass
    def start(self):pass
app.HotkeyThread=NoHotkey
checks=[]
def pump():
    for _ in range(4):root.update();time.sleep(.02)
with tempfile.TemporaryDirectory(prefix='tool-sizes-',dir=Path(__file__).parent) as folder:
    app.STATE_FILE=os.path.join(folder,'state.json')
    Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'auto_on_v2':True,'active':[],'level':26}),encoding='utf-8')
    root=tk.Tk();errors=[];root.report_callback_exception=lambda x,y,z:errors.append(str(y))
    a=app.App(root);a.db.load_indexes()
    for scale in widgets.TEXT_SCALES:
        a.set_text_size(scale);a.ui_tools();w=a._tools_window;w.geometry('440x640');pump()
        for key in ('session','route','timers','saved','compare','quick'):
            a._utility_show(key);pump()
            buttons=[b for b in ui_walk_widgets(w) if isinstance(b,tk.Button) and b.winfo_ismapped()]
            assert buttons, (scale,key,'No visible actions')
            clipped=[b.cget('text') for b in buttons if b.winfo_x()<0 or b.winfo_x()+b.winfo_width()>b.master.winfo_width()+1 or b.winfo_width()<b.winfo_reqwidth()-1]
            assert not clipped,(scale,key,clipped)
            checks.append(f'{key}: visible actions fit at {round(scale*100)}% / 440px')
        w.destroy();pump()
    assert not errors,errors
    checks.append('No callback errors')
    for job in root.tk.call('after','info'):root.tk.call('after','cancel',job)
    root.destroy()
report={'ok':True,'count':len(checks),'checks':checks}
Path(__file__).with_name('tool-sizes-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
